import asyncio
import logging

import d20
import discord
from sqlalchemy import select, false, func
from sqlalchemy.exc import NoResultFound
from Discord.Bot import bot

import Systems.Base.Character
from Backend.Database.database_models import get_tracker, get_condition, get_macro, Character_Vault
from Backend.utils.error_handling_reporting import error_not_initialized, ErrorReport
from Backend.utils import utils
from Backend.utils.Char_Getter import get_character
from Backend.Database.engine import async_session
import Backend.Database.engine


class Utilities:
    """
    Utilites Class. Contains methods for adding and copying characters.
    """

    def __init__(self, ctx, guild, engine):
        self.ctx = ctx
        self.guild = guild
        self.engine = Backend.Database.engine.engine

    async def add_character(self, bot, name: str, hp: int, player_bool: bool, init: str, image: str = None, **kwargs):
        """
        Adds a character into the database.

        :param bot:
        :param name: string - Needs to be unique
        :param hp: - Integer
        :param player_bool: boolean
        :param init: string
        :param image: string - Link
        :return: boolean - True for sucess, false for failure
        """

        if "multi" in kwargs.keys():
            multi = kwargs["multi"]
        else:
            multi = 1
        embeds = []

        logging.info("add_character")
        try:
            for x in range(0, multi):
                if multi > 1:
                    modifier = f" {utils.NPC_Iterator[x]}"
                else:
                    modifier = ""

                item_name = f"{name} {modifier}"

                new_hp = d20.roll(f"{hp}").total
                initiative = 0
                if self.guild.initiative is not None:
                    try:
                        roll = d20.roll(init)
                        initiative = roll.total
                    except ValueError:
                        await self.ctx.channel.send(f"Invalid Initiative String `{init}`, Please check and try again.")
                        return False
                    except Exception:
                        initiative = 0

                async with async_session() as session:
                    Tracker = await get_tracker(self.ctx, id=self.guild.id)
                    async with session.begin():
                        tracker = Tracker(
                            name=item_name,
                            init_string=init,
                            init=initiative,
                            player=player_bool,
                            user=self.ctx.user.id,
                            current_hp=new_hp,
                            max_hp=new_hp,
                            temp_hp=0,
                            pic=image,
                        )
                        session.add(tracker)
                    await session.commit()

                    success = discord.Embed(
                        title=item_name.title(),
                        fields=[discord.EmbedField(name="Success", value="Successfully Imported")],
                        color=discord.Color.dark_gold(),
                    )
                    try:
                        Character_Model = await get_character(item_name, self.ctx)
                        success.set_thumbnail(url=Character_Model.pic)
                    except AttributeError:
                        success.set_thumbnail(url=Systems.Base.Character.default_pic)
                    embeds.append(success)
            await self.ctx.respond(embeds=embeds[:9])
            embeds = embeds[9:]
            while len(embeds) > 0:
                await self.ctx.channel.send(embeds=embeds[:9])
                embeds = embeds[9:]
            return True
        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"add_character: {e}")
            report = ErrorReport(self.ctx, "add_character", e, bot)
            await report.report()
            return False

    async def copy_character(self, name: str, new_name: str):
        logging.info("copy_character")
        try:
            Tracker = await get_tracker(self.ctx, id=self.guild.id)
            Condition = await get_condition(self.ctx, id=self.guild.id)
            Macro = await get_macro(self.ctx, id=self.guild.id)

            # Load up the old character

            split_name = name.split(",")
            async with async_session() as session:
                if len(split_name) > 1:
                    character = await self.retreive_from_vault(name)
                    guild_id = int(split_name[1])
                else:
                    char_result = await session.execute(select(Tracker).where(Tracker.name == name))
                    character = char_result.scalars().one()
                    guild_id = self.guild.id

                # If initiative is active, roll initiative
                initiative = 0
                if self.guild.initiative is not None:
                    try:
                        roll = d20.roll(character.init_string)
                        initiative = roll.total
                    except Exception:
                        initiative = 0

                # Copy the character over into a new character with a new name
            async with session.begin():
                new_char = Tracker(
                    name=new_name,
                    init_string=character.init_string,
                    init=initiative,
                    player=character.player,
                    user=character.user,
                    current_hp=character.current_hp,
                    max_hp=character.max_hp,
                    temp_hp=character.temp_hp,
                    pic=character.pic,
                )
                session.add(new_char)
            await session.commit()

            # Load the new character from the database, to get its ID
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == new_name))
                new_character = char_result.scalars().one()

            # Copy conditions
            async with async_session() as session:
                Search_Con = await get_condition(self.ctx, id=guild_id)
                con_result = await session.execute(
                    select(Search_Con)
                    .where(Search_Con.character_id == character.id)
                    .where(Search_Con.visible == false())
                )
                conditions = con_result.scalars().all()

            async with session.begin():
                for condit in conditions:
                    await asyncio.sleep(0)
                    new_condition = Condition(
                        character_id=new_character.id,
                        counter=condit.counter,
                        title=condit.title,
                        number=condit.number,
                        auto_increment=condit.auto_increment,
                        time=condit.time,
                        visible=condit.visible,
                    )
                    session.add(new_condition)
                await session.commit()

            # Copy Macros
            async with async_session() as session:
                Search_Macro = await get_macro(self.ctx, id=guild_id)
                macro_result = await session.execute(
                    select(Search_Macro).where(Search_Macro.character_id == character.id)
                )
                macros = macro_result.scalars().all()

            async with session.begin():
                for mac in macros:
                    await asyncio.sleep(0)
                    new_macro = Macro(character_id=new_character.id, name=mac.name, macro=mac.macro)
                    session.add(new_macro)
                await session.commit()

            return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"copy_character: {e}")
            return False

    async def delete_character(self, character: str):
        logging.info("delete_Character")
        try:
            # load tables

            Tracker = await get_tracker(self.ctx, id=self.guild.id)
            Condition = await get_condition(self.ctx, id=self.guild.id)
            Macro = await get_macro(self.ctx, id=self.guild.id)

            async with async_session() as session:
                # print(character)
                result = await session.execute(select(Tracker).where(func.lower(Tracker.name) == character.lower()))
                char = result.scalars().one()
                # print(char.id)
                result = await session.execute(select(Condition).where(Condition.character_id == char.id))
                Condition_list = result.scalars().all()
                # print(Condition_list)
                result = await session.execute(select(Macro).where(Macro.character_id == char.id))
                Macro_list = result.scalars().all()
            # Delete Conditions
            for con in Condition_list:
                await asyncio.sleep(0)
                async with async_session() as session:
                    await session.delete(con)
                    await session.commit()
            # Delete Macros
            for mac in Macro_list:
                await asyncio.sleep(0)
                async with async_session() as session:
                    await session.delete(mac)
                    await session.commit()
            # Delete the Character
            async with async_session() as session:
                await session.delete(char)
                await session.commit()
            try:
                await self.ctx.channel.send(f"{char.name} Deleted")
            except Exception:
                await bot.get_channel(self.guild.tracker_channel).send(f"{char.name} Deleted")
            return True
        except Exception as e:
            logging.warning(f"delete_character: {e}")
            return False

    async def edit_attack(self, character, attack, dmg_stat, attk_stat, crit, dmg, prof):
        await self.ctx.channel.send("Command Disabled for current system")
        return False

    async def edit_resistances(self, character, element, resist_weak, ammount):
        await self.ctx.channel.send("Command Disabled for current system")
        return False

    async def add_to_vault(self, char_name):
        try:
            logging.info(f"Writing {char_name} to Vault")
            Tracker = await get_tracker(self.ctx, id=self.guild.id)
            async with async_session() as tracker_session:
                result = await tracker_session.execute(
                    select(Tracker).where(func.lower(Tracker.name) == char_name.lower())
                )
                character = result.scalars().one()
                # print(character.name)
                try:
                    async with async_session() as write_session:
                        query = await write_session.execute(
                            select(Character_Vault)
                            .where(func.lower(Character_Vault.name) == character.name.lower())
                            .where(Character_Vault.guild_id == self.guild.id)
                        )
                        character_data = query.scalars().one()

                        character_data.guild_id = self.guild.id
                        character_data.disc_guild_id = self.guild.guild_id
                        character_data.system = self.guild.system
                        character_data.name = character.name
                        character_data.user = character.user

                        await write_session.commit()
                        # print("success old")
                except Exception:
                    async with write_session.begin():
                        new_char = Character_Vault(
                            guild_id=self.guild.id,
                            system=self.guild.system,
                            name=character.name,
                            user=character.user,
                            disc_guild_id=self.guild.guild_id,
                        )
                        write_session.add(new_char)
                    await write_session.commit()
                    # print("success new")
            return True
        except Exception:
            return False

    async def delete_from_vault(self, char_name):
        try:
            logging.info(f"Deleting {char_name} from Vault")

            async with async_session() as session:
                result = await session.execute(
                    select(Character_Vault)
                    .where(Character_Vault.name == char_name)
                    .where(Character_Vault.guild_id == self.guild.id)
                )
                character = result.scalars().one()

            async with async_session() as session:
                await session.delete(character)
                await session.commit()
            return True
        except Exception:
            return False

    async def retreive_from_vault(self, char_name):
        logging.info("retreiving from vault")

        split_name = char_name.split(",")
        name = split_name[0]
        guild_id = int(split_name[1])
        # print(guild_id)

        Tracker = await get_tracker(self.ctx, id=guild_id, system=self.guild.system)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == name))
            character = result.scalars().one()
        return character
