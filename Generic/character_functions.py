# imports
import asyncio
import datetime
import inspect
import logging
import os
import sys

import d20
import discord

from dotenv import load_dotenv
from sqlalchemy import select, false
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# import D4e.d4e_functions
import PF2e.pf2_functions
import time_keeping_functions

from database_models import get_tracker, get_condition, get_macro
from error_handling_reporting import error_not_initialized, ErrorReport
# from initiative import get_guild, PF2AddCharacterModal, D4eAddCharacterModal, update_pinned_tracker
from utils.Char_Getter import get_character
from utils.utils import get_guild

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


async def add_character(ctx: discord.ApplicationContext, engine, bot, name: str, hp: int, player_bool: bool, init: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)

        initiative = 0
        if guild.initiative is not None:
            try:
                roll = d20.roll(init)
                initiative = roll.total
            except ValueError:
                await ctx.channel.send(f"Invalid Initiative String `{init}`, Please check and try again.")
                return False
            except Exception:
                initiative = 0

        if guild.system == "PF2":
            pf2Modal = PF2AddCharacterModal(
                name=name,
                hp=hp,
                init=init,
                initiative=initiative,
                player=player_bool,
                ctx=ctx,
                engine=engine,
                bot=bot,
                title=name,
            )
            await ctx.send_modal(pf2Modal)
            return True
        elif guild.system == "D4e":
            D4eModal = D4eAddCharacterModal(
                name=name,
                hp=hp,
                init=init,
                initiative=initiative,
                player=player_bool,
                ctx=ctx,
                engine=engine,
                bot=bot,
                title=name,
            )
            await ctx.send_modal(D4eModal)
            return True
        else:
            async with async_session() as session:
                Tracker = await get_tracker(ctx, engine, id=guild.id)
                async with session.begin():
                    tracker = Tracker(
                        name=name,
                        init_string=init,
                        init=initiative,
                        player=player_bool,
                        user=ctx.user.id,
                        current_hp=hp,
                        max_hp=hp,
                        temp_hp=0,
                    )
                    session.add(tracker)
                await session.commit()

        await engine.dispose()
        await update_pinned_tracker(ctx, engine, bot)
        return True
    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"add_character: {e}")
        report = ErrorReport(ctx, add_character.__name__, e, bot)
        await report.report()
        return False


async def edit_character(
    ctx: discord.ApplicationContext,
    engine,
    bot,
    name: str,
    hp: int,
    init: str,
    active: bool,
    player: discord.User,
    guild=None,
):
    logging.info("edit_character")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, guild)
        Tracker = await get_tracker(ctx, engine, id=guild.id)

        # Give an error message if the character is the active character and making them inactive
        if guild.saved_order == name:
            await ctx.channel.send(
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
            if active is not None and guild.saved_order != name:
                character.active = active

            await session.commit()
        if guild.system == "PF2":
            response = await PF2e.pf2_functions.edit_stats(ctx, engine, bot, name)
            if response:
                # await update_pinned_tracker(ctx, engine, bot)
                return True
            else:
                return False
        elif guild.system == "D4e":
            response = await D4e.d4e_functions.edit_stats(ctx, engine, bot, name)
            if response:
                # await update_pinned_tracker(ctx, engine, bot)
                return True
            else:
                return False
        else:
            await ctx.respond(f"Character {name} edited successfully.", ephemeral=True)
            await update_pinned_tracker(ctx, engine, bot)
            await engine.dispose()
            return True

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"add_character: {e}")
        report = ErrorReport(ctx, add_character.__name__, e, bot)
        await report.report()
        return False


async def copy_character(ctx: discord.ApplicationContext, engine, bot, name: str, new_name: str):
    logging.info("copy_character")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        Macro = await get_macro(ctx, engine, id=guild.id)

        # Load up the old character
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == name))
            character = char_result.scalars().one()

        # If initiative is active, roll initiative
        initiative = 0
        if guild.initiative is not None:
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
            )
            session.add(new_char)
        await session.commit()

        # Load the new character from the database, to get its ID
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == new_name))
            new_character = char_result.scalars().one()

        # Copy conditions
        async with async_session() as session:
            con_result = await session.execute(
                select(Condition).where(Condition.character_id == character.id).where(Condition.visible == false())
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
            macro_result = await session.execute(select(Macro).where(Macro.character_id == character.id))
            macros = macro_result.scalars().all()

        async with session.begin():
            for mac in macros:
                await asyncio.sleep(0)
                new_macro = Macro(character_id=new_character.id, name=mac.name, macro=mac.macro)
                session.add(new_macro)
            await session.commit()

        await engine.dispose()
        return True

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning("add_character: {e}")
        report = ErrorReport(ctx, copy_character.__name__, e, bot)
        await report.report()
        return False


async def delete_character(ctx: discord.ApplicationContext, character: str, engine, bot):
    logging.info("delete_Character")
    try:
        # load tables
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        Macro = await get_macro(ctx, engine, id=guild.id)

        async with async_session() as session:
            # print(character)
            result = await session.execute(select(Tracker).where(Tracker.name == character))
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
        await ctx.channel.send(f"{char.name} Deleted")

        await engine.dispose()
        return True
    except Exception as e:
        logging.warning(f"delete_character: {e}")
        report = ErrorReport(ctx, delete_character.__name__, e, bot)
        await report.report()
        return False


async def get_char_sheet(ctx: discord.ApplicationContext, engine, bot: discord.Bot, name: str, guild=None):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        # Load the tables
        guild = await get_guild(ctx, guild)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        if guild.system == "EPF":
            character = await get_character(name, ctx, guild=guild, engine=engine)
            user = bot.get_user(character.character_model.user).name
            if character.character_model.player:
                status = "PC:"
            else:
                status = "NPC:"

            condition_list = await character.conditions(ctx)

            embed = discord.Embed(
                title=f"{name}",
                fields=[
                    discord.EmbedField(name="Name: ", value=character.character_model.name, inline=False),
                    discord.EmbedField(name=status, value=user, inline=False),
                    discord.EmbedField(
                        name="HP: ",
                        value=f"{character.current_hp}/{character.max_hp}: ({character.temp_hp} Temp)",
                        inline=False,
                    ),
                    discord.EmbedField(name="Initiative: ", value=character.init_string, inline=False),
                ],
                color=discord.Color.dark_gold(),
            )
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
                            name=item.title, value=await time_keeping_functions.time_left(ctx, engine, bot, item.number)
                        )
                    )
            print("returning 3")
            return [embed, counter_embed, condition_embed]
            # else:
            #     print("returning 1")
            #     return [embed]

        else:
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == name))
                character = result.scalars().one()
            async with async_session() as session:
                result = await session.execute(
                    select(Condition).where(Condition.character_id == character.id).order_by(Condition.title.asc())
                )
                condition_list = result.scalars().all()

            user = bot.get_user(character.user).name
            if character.player:
                status = "PC:"
            else:
                status = "NPC:"
            con_dict = {}

            for item in condition_list:
                con_dict[item.title] = item.number

            embed = discord.Embed(
                title=f"{name}",
                fields=[
                    discord.EmbedField(name="Name: ", value=character.name, inline=False),
                    discord.EmbedField(name=status, value=user, inline=False),
                    discord.EmbedField(
                        name="HP: ",
                        value=f"{character.current_hp}/{character.max_hp}: ( {character.temp_hp} Temp)",
                        inline=False,
                    ),
                    discord.EmbedField(name="Initiative: ", value=character.init_string, inline=False),
                ],
                color=discord.Color.dark_gold(),
            )
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
                            name=item.title, value=await time_keeping_functions.time_left(ctx, engine, bot, item.number)
                        )
                    )

            return [embed, counter_embed, condition_embed]
    except Exception as e:
        logging.info(f"get character sheet: {e}")
        report = ErrorReport(ctx, get_char_sheet.__name__, e, bot)
        await report.report()