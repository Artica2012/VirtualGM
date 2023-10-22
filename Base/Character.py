# imports
import asyncio
import datetime
import logging
import os

import d20
import discord
from dotenv import load_dotenv
from sqlalchemy import select, false, true, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import time_keeping_functions
from database_models import get_tracker, get_condition
from error_handling_reporting import error_not_initialized
from time_keeping_functions import get_time

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    # TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    # TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")

default_pic = (
    "https://cdn.discordapp.com/attachments/1028702442927431720/1107574197061963807/"
    "artica_A_portrait_of_a_generic_fantasy_character._Cloaked_in_sh_b571634a-b297-4e86-a57a-496ce438dd0b.png"
)


class Character:
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, guild=None):
        """
        Character Class. This is the character model. The base class contains the basic character model which each
        individual system subclasses from.

        This class should not be invoked directly, but should be called via the utils.get_character function as this
        will asynchronously query the database and then feed the data into the character model.
        :param char_name: string
        :param ctx: discord application context
        :param engine:
        :param character: character data from the database via get_character function output
        :param guild:
        """
        self.char_name = char_name
        self.ctx = ctx
        self.guild = guild
        self.engine = engine
        self.id = character.id
        self.name = character.name
        self.player = character.player
        self.user = character.user
        self.current_hp = character.current_hp
        self.max_hp = character.max_hp
        self.temp_hp = character.temp_hp
        self.init_string = character.init_string
        self.init = character.init
        self.active = character.active
        self.character_model = character
        self.pic = character.pic if character.pic is not None else default_pic  # uses the default picture if none is
        # supplied

    async def character(self):
        """
        Queries the database and returns the character model. Used for the update method, as this data is usually stored
        in self.character_model

        :return: Database Tracker object
        """

        logging.info("Loading Character")
        if self.guild is not None:
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        else:
            Tracker = await get_tracker(self.ctx, self.engine)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Tracker).where(func.lower(Tracker.name) == self.char_name.lower())
                )
                character = result.scalars().one()
            return character

        except NoResultFound:
            return None

    async def conditions(self, no_time=False):
        """
        Returns conditions from the condition database associated with the character.

        :param no_time: bool - Default false. If true, excludes time based conditions
        :return: List of condition objects
        """
        logging.info("Returning PF2 Character Conditions")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        if self.guild is not None:
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
        else:
            Condition = await get_condition(self.ctx, self.engine)
        try:
            async with async_session() as session:
                if no_time:
                    result = await session.execute(
                        select(Condition.title)
                        .where(Condition.character_id == self.id)
                        .where(Condition.time == false())
                        .where(Condition.visible == true())
                        .order_by(Condition.title.asc())
                    )
                else:
                    result = await session.execute(
                        select(Condition)
                        .where(Condition.character_id == self.id)
                        .where(Condition.visible == true())
                        .order_by(Condition.title.asc())
                    )
                return result.scalars().all()
        except NoResultFound:
            return []

    async def set_hp(self, amount: int):
        """
        Sets the hp property of the character to the specified value and writes it to the database.
        :param amount: integer
        :return: No return value
        """
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
            character = char_result.scalars().one()
            character.current_hp = amount
            await session.commit()
            await self.update()

    async def change_hp(self, amount: int, heal: bool, post=True):
        """
        Changes the health value by the set amount and writes it to the database.
        If post == True, then it sends a message with the hp change. Intelligently avoids taking HP below 0 or above the
        maximum.
        :param amount: integer
        :param heal: boolean. True adds the amount to health, false subtracts it
        :param post: boolean. Default is True. If false, does not send a message with the result.
        :return: boolean. True for success, False for failure.
        """
        logging.info("Edit HP")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            try:
                Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            except AttributeError:
                Tracker = await get_tracker(self.ctx, self.engine)
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
                character = char_result.scalars().one()

                chp = character.current_hp
                new_hp = chp
                maxhp = character.max_hp
                thp = character.temp_hp
                new_thp = 0

                # Bottom out at 0 for everyone else
                if heal:
                    new_hp = chp + amount
                    if new_hp > maxhp:
                        new_hp = maxhp
                if not heal:
                    if thp == 0:
                        new_hp = chp - amount
                        if new_hp < 0:
                            new_hp = 0
                    else:
                        if thp > amount:
                            new_thp = thp - amount
                            new_hp = chp
                        else:
                            new_thp = 0
                            new_hp = chp - amount + thp
                        if new_hp < 0:
                            new_hp = 0

                character.current_hp = new_hp
                character.temp_hp = new_thp
                await session.commit()
                await self.update()
            if post:
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
            return True
        except Exception as e:
            logging.warning(f"change_hp: {e}")
            return False

    async def calculate_hp(self):
        """
        Takes the current hp vs max hp and calculates injured, critical etc.
        :return: String with the interpreted health value.
        """
        logging.info("Calculate hp")
        hp = self.current_hp / self.max_hp
        if hp == 1:
            hp_string = "Uninjured"
        elif hp > 0.5:
            hp_string = "Injured"
        elif hp >= 0.1:
            hp_string = "Bloodied"
        elif hp > 0:
            hp_string = "Critical"
        else:
            hp_string = "Dead"

        return hp_string

    async def add_thp(self, amount: int):
        """
        Adds to the tHP parameter and writes it to the database
        :param amount: integer
        :return: boolean. True if successful, false for failure
        """

        logging.info(f"add_thp {amount}")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.char_name))
                character = char_result.scalars().one()
                character.temp_hp = character.temp_hp + amount
                await session.commit()
            await self.update()
            return True
        except Exception as e:
            logging.warning(f"add_thp: {e}")
            return False

    # Set the initiative
    async def set_init(self, init, **kwargs):
        """
        Sets the initiative parameter.
        :param init: integer or string. If string, it will roll the string, if integer, will use the integer.
        :param update: If true, updates the medel afterwards.
        :return: String
        """
        if "update" in kwargs.keys():
            update = kwargs["update"]
        else:
            update = True

        logging.info(f"set_init {self.char_name} {init}")
        if self.ctx is None and self.guild is None:
            raise LookupError("No guild reference")
        if type(init) == str:
            roll = d20.roll(init)
            init = roll.total
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            if self.guild is None:
                Tracker = await get_tracker(
                    self.ctx,
                    self.engine,
                )
            else:
                Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.char_name))
                character = char_result.scalars().one()
                character.init = init
                await session.commit()
            if update:
                await self.update()
            return f"Initiative set to {init} for {self.char_name}"
        except Exception as e:
            logging.error(f"set_init: {e}")
            return f"Failed to set initiative: {e}"

    async def update(self):
        logging.info(f"Updating character: {self.char_name}")
        self.character_model = await self.character()
        self.char_name = self.character_model.name
        self.id = self.character_model.id
        self.name = self.character_model.name
        self.player = self.character_model.player
        self.user = self.character_model.user
        self.current_hp = self.character_model.current_hp
        self.max_hp = self.character_model.max_hp
        self.temp_hp = self.character_model.max_hp
        self.init_string = self.character_model.init_string
        self.init = self.character_model.init

    async def set_cc(
        self,
        title: str,
        counter: bool,
        number: int,
        unit: str,
        auto_decrement: bool,
        flex: bool = False,
        data: str = "",
        target: str = None,
    ):
        logging.info("set_cc")
        # Get the Character's data

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)

        if target is None:
            target = self.char_name
            target_id = self.character_model.id
        else:
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                result = await session.execute(select(Tracker.id).where(func.lower(Tracker.name) == target.lower()))
                target_id = result.scalars().one()

        # Check to make sure there isn't a condition with the same name on the character
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == self.id).where(Condition.title == title)
            )
            check_con = result.scalars().all()
            if len(check_con) > 0:
                return False

        # Write the condition to the table
        try:
            if not self.guild.timekeeping or unit == "Round":  # If its not time based, then just write it
                async with session.begin():
                    condition = Condition(
                        character_id=self.id,
                        title=title,
                        number=number,
                        counter=counter,
                        auto_increment=auto_decrement,
                        time=False,
                        flex=flex,
                        target=target_id,
                    )
                    session.add(condition)
                await session.commit()
                # await update_pinned_tracker(ctx, engine, bot)
                return True

            else:  # If its time based, then calculate the end time, before writing it
                current_time = await get_time(self.ctx, self.engine)
                if unit == "Minute":
                    end_time = current_time + datetime.timedelta(minutes=number)
                elif unit == "Hour":
                    end_time = current_time + datetime.timedelta(hours=number)
                else:
                    end_time = current_time + datetime.timedelta(days=number)

                timestamp = end_time.timestamp()

                async with session.begin():
                    condition = Condition(
                        character_id=self.id,
                        title=title,
                        number=timestamp,
                        counter=counter,
                        auto_increment=True,
                        time=True,
                        target=target_id,
                    )
                    session.add(condition)
                await session.commit()
                # await update_pinned_tracker(ctx, engine, bot)
                return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"set_cc: {e}")
            return False

    # Delete CC
    async def delete_cc(self, condition):
        logging.info("delete_Cc")
        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Condition)
                    .where(Condition.character_id == self.id)
                    .where(Condition.visible == true())
                    .where(Condition.title == condition)
                )
                con_list = result.scalars().all()
            if len(con_list) == 0:
                return False

            for con in con_list:
                await asyncio.sleep(0)
                async with async_session() as session:
                    await session.delete(con)
                    await session.commit()
            return True
        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"delete_cc: {e}")
            return False

    async def edit_cc(self, condition: str, value: int):
        logging.info("edit_cc")

        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Condition).where(Condition.character_id == self.id).where(Condition.title == condition)
                )
                condition = result.scalars().one()

                if condition.time:
                    await self.ctx.send_followup(
                        "Unable to edit time based conditions. Try again in a future update.", ephemeral=True
                    )
                    return False
                else:
                    condition.number = value
                    await session.commit()
            return True
        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"edit_cc: {e}")
            return False

    async def check_time_cc(self, bot=None):
        logging.info("Clean CC")
        current_time = await get_time(self.ctx, self.engine, guild=self.guild)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Condition = await get_condition(self.ctx, self.engine, self.guild.id)
        del_result = False
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == self.id).where(Condition.time == true())
            )
            con_list = result.scalars().all()

        for row in con_list:
            await asyncio.sleep(0)
            time_stamp = datetime.datetime.fromtimestamp(row.number)
            time_left = time_stamp - current_time
            if time_left.total_seconds() <= 0:
                del_result = await self.delete_cc(row.title)
            if del_result:
                if self.ctx is not None:
                    await self.ctx.channel.send(f"{row.title} removed from {self.char_name}")
                elif bot is not None:
                    tracker_channel = bot.get_channel(self.guild.tracker_channel)
                    await tracker_channel.send(f"{row.title} removed from {self.char_name}")

    async def get_char_sheet(self, bot):
        try:
            if self.character_model.player:
                status = "PC:"
            else:
                status = "NPC:"
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                result = await session.execute(
                    select(Condition)
                    .where(Condition.character_id == self.id)
                    .where(Condition.visible == true())
                    .order_by(Condition.title.asc())
                )

                condition_list = result.scalars().all()

            user_name = bot.get_user(self.user).name

            embed = discord.Embed(
                title=f"{self.char_name}",
                fields=[
                    discord.EmbedField(name="Name: ", value=self.char_name, inline=False),
                    discord.EmbedField(name=status, value=user_name, inline=False),
                    discord.EmbedField(
                        name="HP: ",
                        value=f"{self.current_hp}/{self.max_hp}: ({self.temp_hp} Temp)",
                        inline=False,
                    ),
                    discord.EmbedField(name="Initiative: ", value=self.init_string, inline=False),
                ],
                color=discord.Color.dark_gold(),
            )
            embed.set_thumbnail(url=self.pic)
            # if condition_list != None:
            condition_embed = discord.Embed(
                title="Conditions",
                fields=[],
                color=discord.Color.dark_teal(),
            )
            counter_embed = discord.Embed(
                title="Counters",
                fields=[],
                color=discord.Color.dark_magenta(),
            )
            for item in condition_list:
                await asyncio.sleep(0)
                if not item.visible:
                    embed.fields.append(discord.EmbedField(name=item.title, value=item.number, inline=True))
                elif item.visible and not item.time:
                    if not item.counter:
                        condition_embed.fields.append(discord.EmbedField(name=item.title, value=item.number))
                    elif item.counter:
                        if item.number != 0:
                            counter_embed.fields.append(discord.EmbedField(name=item.title, value=item.number))
                        else:
                            counter_embed.fields.append(discord.EmbedField(name=item.title, value="_"))
                elif item.visible and item.time and not item.counter:
                    condition_embed.fields.append(
                        discord.EmbedField(
                            name=item.title,
                            value=await time_keeping_functions.time_left(self.ctx, self.engine, bot, item.number),
                        )
                    )
            return [embed, counter_embed, condition_embed]
        except NoResultFound:
            await self.ctx.respond(error_not_initialized, ephemeral=True)
            return False
        except IndexError:
            await self.ctx.respond("Ensure that you have added characters to the initiative list.")
        except Exception:
            await self.ctx.respond("Failed")

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
                await self.update()
                success = discord.Embed(
                    title=name.title(),
                    fields=[discord.EmbedField(name="Success", value="Successfully Updated")],
                    color=discord.Color.dark_gold(),
                )
                success.set_thumbnail(url=self.pic)
                await self.ctx.respond(embed=success)
                return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"add_character: {e}")
            return False

    async def set_pic(self, url):
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        try:
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == self.char_name))
                character = result.scalars().one()
                character.pic = url
                await session.commit()
            return True
        except Exception:
            return False

    async def get_pic(self):
        return self.character_model.pic
