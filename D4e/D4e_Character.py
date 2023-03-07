# imports
import asyncio
import datetime
import logging
import os
import inspect
import sys

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

import warnings
from sqlalchemy import exc


async def get_D4e_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating PF2_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    tracker = await get_tracker(char_name, ctx, id=guild.id)
    condition = await get_condition(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(tracker).where(tracker.name == char_name))
            character = result.scalars().one()
        async with async_session() as session:
            result = await session.execute(
                select(condition).where(condition.id == character.id).where(condition.visible == false()))
            stats_list = result.scalars().all()
            stats = {}
            for item in stats_list:
                stats[f"{item.title}"] = item.number
            return D4e_Character(char_name, ctx, engine, character, stats, guild=guild)

    except NoResultFound:
        return None


class D4e_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, stats, guild):
        self.ac = stats['AC']
        self.fort = stats["Fort"]
        self.reflex = stats["Reflex"]
        self.will = stats["Will"]
        super().__init__(char_name, ctx, engine, character, guild)

    async def conditions(self, no_time=False, flex=False):
        logging.info("Returning PF2 Character Conditions")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        if self.guild is not None:
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
        else:
            Condition = await get_condition(self.ctx, self.engine)
        try:
            async with async_session() as session:
                if no_time and not flex:
                    result = await session.execute(
                        select(Condition.title)
                            .where(Condition.character_id == self.id)
                            .where(Condition.time == false())
                            .where(Condition.visible == true())
                            .order_by(Condition.title.asc())
                    )
                elif flex and not no_time:
                    result = await session.execute(
                        select(Condition.title)
                            .where(Condition.character_id == self.id)
                            .where(Condition.visible == true())
                            .where(Condition.flex == true())
                            .order_by(Condition.title.asc())
                    )
                elif flex and no_time:
                    result = await session.execute(
                        select(Condition.title)
                            .where(Condition.character_id == self.id)
                            .where(Condition.time == false())
                            .where(Condition.visible == true())
                            .where(Condition.flex == true())
                            .order_by(Condition.title.asc())
                    )
                else:
                    result = await session.execute(select(Condition)
                                                   .where(Condition.character_id == self.id)
                                                   .where(Condition.visible == true())
                                                   .order_by(Condition.title.asc()))
                return result.scalars().all()
        except NoResultFound:
            return []

    async def change_hp(self, amount: int, heal: bool):
        logging.info("Edit HP")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
                character = char_result.scalars().one()

                chp = character.current_hp
                new_hp = chp
                maxhp = character.max_hp
                thp = character.temp_hp
                new_thp = 0

                # If its D4e, let the HP go below 0, but start healing form 0.
                # Bottom out at 0 for everyone else
                if heal:
                    if chp < 0:
                        chp = 0
                    new_hp = chp + amount
                    if new_hp > maxhp:
                        new_hp = maxhp
                if not heal:
                    if thp == 0:
                        new_hp = chp - amount
                    else:
                        if thp > amount:
                            new_thp = thp - amount
                            new_hp = chp
                        else:
                            new_thp = 0
                            new_hp = chp - amount + thp

                character.current_hp = new_hp
                character.temp_hp = new_thp
                await session.commit()
                await self.update()

            if character.player:  # Show the HP it its a player
                if heal:
                    await self.ctx.send_followup(
                        f"{self.name} healed for {amount}. New HP: {new_hp}/{character.max_hp}")
                else:
                    await self.ctx.send_followup(
                        f"{self.name} damaged for {amount}. New HP: {new_hp}/{character.max_hp}")
            else:  # Obscure the HP if its an NPC
                if heal:
                    await self.ctx.send_followup(
                        f"{self.name} healed for {amount}. {await self.calculate_hp()}")
                else:
                    await self.ctx.send_followup(
                        f"{self.name} damaged for {amount}. {await self.calculate_hp()}")
            await self.update()
            return True
        except Exception as e:
            logging.warning(f"change_hp: {e}")
            return False

    async def edit_character(self,
                             name: str,
                             hp: int,
                             init: str,
                             active: bool,
                             player: discord.User,
                             bot
                             ):
        logging.info("edit_character")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            # Give an error message if the character is the active character and making them inactive
            if self.guild.saved_order == name:
                await self.ctx.channel.send(
                    "Unable to inactivate a character while they are the active character in initiative.  Please advance"
                    " turn and try again."
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

            response = await edit_stats(self.ctx, self.engine, name, bot)
            if response:
                # await update_pinned_tracker(ctx, engine, bot)
                return True
            else:
                return False
            #
            # await ctx.respond(f"Character {name} edited successfully.", ephemeral=True)
            # await update_pinned_tracker(ctx, engine, bot)
            # await engine.dispose()
            # return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"add_character: {e}")
            report = ErrorReport(self.ctx, "edit_character", e, bot)
            await report.report()
            return False


async def edit_stats(ctx, engine, name: str, bot):
    try:
        if engine == None:
            engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        guild = await get_guild(ctx, None)

        Character_Model = await get_D4e_Character(name, ctx, guild=guild, engine=engine)
        condition_dict = {}
        for con in await Character_Model.conditions():
            await asyncio.sleep(0)
            condition_dict[con.title] = con.number
        editModal = D4eEditCharacterModal(
            character=await Character_Model.character(), cons=condition_dict, ctx=ctx, engine=engine, title=name,
            bot=bot
        )
        await ctx.send_modal(editModal)

        return True

    except Exception:
        return False


# D&D 4e Specific
class D4eEditCharacterModal(discord.ui.Modal):
    def __init__(self, character, cons: dict, ctx: discord.ApplicationContext, engine, bot, *args, **kwargs):
        self.character = character
        self.cons = (cons,)
        self.name = character.name
        self.player = ctx.user.id
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
        super().__init__(
            discord.ui.InputText(label="AC", placeholder="Armor Class", value=cons["AC"]),
            discord.ui.InputText(label="Fort", placeholder="Fortitude", value=cons["Fort"]),
            discord.ui.InputText(label="Reflex", placeholder="Reflex", value=cons["Reflex"]),
            discord.ui.InputText(label="Will", placeholder="Will", value=cons["Will"]),
            *args,
            **kwargs,
        )

    async def callback(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_message(f"{self.name} Updated")
        guild = await get_guild(self.ctx, None)

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Character_Model = await get_D4e_Character(self.name, self.ctx, guild=guild, engine=self.engine)

        Condition = await get_condition(self.ctx, self.engine, id=guild.id)

        for item in self.children:
            async with async_session() as session:
                result = await session.execute(
                    select(Condition).where(Condition.character_id == Character_Model.id).where(
                        Condition.title == item.label)
                )
                condition = result.scalars().one()
                condition.number = int(item.value)
                await session.commit()

        # Tracker_Model = await get_tracker_model(self.ctx, self.bot, guild=guild, engine=self.engine)
        # await Tracker_Model.update_pinned_tracker()
        # print('Tracker Updated')
        await self.ctx.channel.send(embeds=await Character_Model.get_char_sheet(self.bot))

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        logging.warning(error)
        self.stop()
