# imports
import logging

import discord
from discord import Interaction
from sqlalchemy import select, false, true, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Character import Character
from database_models import get_tracker, get_condition
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from utils.utils import get_guild

default_pic = (
    "https://cdn.discordapp.com/attachments/1028702442927431720/1107574226816352348/"
    "artica_A_portrait_of_a_generic_fantasy_character._Cloaked_in_sh_ea9fd7f1-e3a4-43f5-96d4-04b6f933b932.png"
)


async def get_D4e_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating D4e_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    tracker = await get_tracker(char_name, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(tracker).where(func.lower(tracker.name) == char_name.lower()))
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
            return D4e_Character(char_name, ctx, engine, character, stats, guild=guild)

    except NoResultFound:
        return None


class D4e_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, stats, guild):
        self.ac = stats["AC"]
        self.fort = stats["Fort"]
        self.reflex = stats["Reflex"]
        self.will = stats["Will"]
        super().__init__(char_name, ctx, engine, character, guild)
        self.pic = character.pic if character.pic is not None else default_pic

    async def conditions(self, no_time=False, flex=False):
        logging.info("Returning D4e Character Conditions")
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
                    result = await session.execute(
                        select(Condition.title)
                        .where(Condition.character_id == self.id)
                        .where(Condition.visible == true())
                        .order_by(Condition.title.asc())
                    )
                return result.scalars().all()

        except NoResultFound:
            return []

    async def change_hp(self, amount: int, heal: bool, post=True):
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
                        f"{self.name} healed for {amount}. New HP: {new_hp}/{character.max_hp}"
                    )
                else:
                    await self.ctx.send_followup(
                        f"{self.name} damaged for {amount}. New HP: {new_hp}/{character.max_hp}"
                    )
            else:  # Obscure the HP if its an NPC
                if heal:
                    await self.ctx.send_followup(f"{self.name} healed for {amount}. {await self.calculate_hp()}")
                else:
                    await self.ctx.send_followup(f"{self.name} damaged for {amount}. {await self.calculate_hp()}")
            await self.update()
            return True
        except Exception as e:
            logging.warning(f"change_hp: {e}")
            return False

    async def edit_character(self, name: str, hp: int, init: str, active: bool, player: discord.User, img: str, bot):
        logging.info("edit_character")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            # Give an error message if the character is the active character and making them inactive
            if self.guild.saved_order == name:
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
                if img != "":
                    character.pic = img

                await session.commit()

            response = await edit_stats(self.ctx, self.engine, name, bot)
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


async def edit_stats(ctx, engine, name: str, bot):
    print("edit_stats")
    try:
        if engine is None:
            engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        guild = await get_guild(ctx, None)

        Character_Model = await get_D4e_Character(name, ctx, guild=guild, engine=engine)
        # condition_dict = {}

        # for con in await Character_Model.conditions():
        #     await asyncio.sleep(0)
        #     print(con)
        #     condition_dict[con.title] = con.number
        # print("GENERATING MODAL")
        # print(condition_dict)
        editModal = D4eEditCharacterModal(character=Character_Model, ctx=ctx, engine=engine, title=name, bot=bot)
        print(editModal)
        result = await ctx.send_modal(editModal)

        return result

    except Exception:
        return False


# D&D 4e Specific
class D4eEditCharacterModal(discord.ui.Modal):
    def __init__(self, character, ctx: discord.ApplicationContext, engine, bot, *args, **kwargs):
        self.character = character
        self.name = character.name
        self.player = ctx.user.id
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
        super().__init__(
            discord.ui.InputText(label="AC", placeholder="Armor Class", value=character.ac),
            discord.ui.InputText(label="Fort", placeholder="Fortitude", value=character.fort),
            discord.ui.InputText(label="Reflex", placeholder="Reflex", value=character.reflex),
            discord.ui.InputText(label="Will", placeholder="Will", value=character.will),
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
                    select(Condition)
                    .where(Condition.character_id == Character_Model.id)
                    .where(Condition.title == item.label)
                )
                condition = result.scalars().one()
                condition.number = int(item.value)
                await session.commit()

        # Tracker_Model = await get_tracker_model(self.ctx, self.bot, guild=guild, engine=self.engine)
        # await Tracker_Model.update_pinned_tracker()
        # print('Tracker Updated')
        await self.ctx.channel.send(embeds=await Character_Model.get_char_sheet(self.bot))
        return True

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        logging.warning(error)
        self.stop()
