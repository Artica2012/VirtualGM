# imports
import logging

import discord
import d20
import sqlalchemy as db
from discord import option, Interaction
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_, select, false, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.ddl import DropTable

import time_keeping_functions
import ui_components

# from utils.Tracker_Getter import get_tracker_model
from utils.utils import get_guild
from database_models import Global
from database_models import get_tracker, get_condition, get_macro
from database_models import get_tracker_table, get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time
from Base.Character import Character

# from utils.Char_Getter import get_character
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized

# from utils.Tracker_Getter import get_tracker_model
from utils.utils import get_guild


async def get_PF2_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating PF2_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(tracker).where(tracker.name == char_name))
            character = result.scalars().one()
        async with async_session() as session:
            result = await session.execute(
                select(Condition)
                .where(Condition.character_id == character.id)
                .where(Condition.visible == false())
                .order_by(Condition.title.asc())
            )
            stat_list = result.scalars().all()
            # print(len(stat_list))
            stats = {}
            for item in stat_list:
                stats[f"{item.title}"] = item.number
            # print(stats)
            return PF2_Character(char_name, ctx, engine, character, stats, guild=guild)

    except NoResultFound:
        return None


class PF2_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, stats, guild):
        self.ac = stats["AC"]
        self.fort = stats["Fort"]
        self.reflex = stats["Reflex"]
        self.will = stats["Will"]
        self.dc = stats["DC"]
        super().__init__(char_name, ctx, engine, character, guild)

    async def edit_character(self, name: str, hp: int, init: str, active: bool, player: discord.User, bot):
        logging.info("edit_character")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            # Give an error message if the character is the active character and making them inactive
            if self.guild.saved_order == name and active is False:
                await self.ctx.channel.send(
                    "Unable to inactivate a character while they are the active character in initiative.  Please"
                    " advance turn and try again."
                )

            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == name))
                character = result.scalars().one()

                if hp is not None:
                    character.max_hp = hp
                if init is not None:
                    character.init_string = str(init)
                if player is not None:
                    character.user = player.id
                if active is not None:
                    character.active = active
                if active is not None and self.guild.saved_order != name:
                    character.active = active

                await session.commit()

                response = await edit_stats(self.ctx, self.engine, bot, name)
                if response:
                    # await update_pinned_tracker(ctx, engine, bot)
                    return True
                else:
                    return False

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"add_character: {e}")
            report = ErrorReport(self.ctx, "edit_character", e, bot)
            await report.report()
            return False


async def edit_stats(ctx, engine, bot, name: str):
    try:
        if engine is None:
            engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        guild = await get_guild(ctx, None)

        Character_Model = await get_PF2_Character(name, ctx, guild=guild, engine=engine)
        editModal = PF2EditCharacterModal(
            character=Character_Model, ctx=ctx, engine=engine, bot=bot, title=Character_Model.char_name
        )
        await ctx.send_modal(editModal)

        return True

    except Exception:
        return False


class PF2EditCharacterModal(discord.ui.Modal):
    def __init__(self, character, ctx: discord.ApplicationContext, engine, bot, *args, **kwargs):
        self.character = character
        self.name = character.char_name
        self.player = ctx.user.id
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
        super().__init__(
            discord.ui.InputText(label="AC", placeholder="Armor Class", value=character.ac),
            discord.ui.InputText(label="Fort", placeholder="Fortitude", value=character.fort),
            discord.ui.InputText(label="Reflex", placeholder="Reflex", value=character.reflex),
            discord.ui.InputText(label="Will", placeholder="Will", value=character.will),
            discord.ui.InputText(label="DC", placeholder="DC", value=character.dc),
            *args,
            **kwargs,
        )

    async def callback(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_message(f"{self.name} Updated")
        guild = await get_guild(self.ctx, None)

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Condition = await get_condition(self.ctx, self.engine, id=guild.id)

        for item in self.children:
            async with async_session() as session:
                result = await session.execute(
                    select(Condition)
                    .where(Condition.character_id == self.character.id)
                    .where(Condition.title == item.label)
                )
                condition = result.scalars().one()
                condition.number = int(item.value)
                await session.commit()

        # Tracker_Model = await get_tracker_model(self.ctx, self.bot, guild=guild, engine=self.engine)
        # await Tracker_Model.update_pinned_tracker()
        await self.ctx.channel.send(embeds=await self.character.get_char_sheet(self.bot))
        return True

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        logging.warning(error)
        self.stop()
