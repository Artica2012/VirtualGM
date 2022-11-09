# initiative.py
# Initiative Tracker Module
import asyncio
import datetime
import logging
import os
import inspect
import sys

# imports
import discord
import sqlalchemy as db
from discord import option, Interaction
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.ddl import DropTable

import D4e.d4e_functions
import PF2e.pf2_functions
from database_models import Global
from database_models import get_tracker, get_condition, get_macro
from database_models import get_tracker_table, get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time

# define global variables

load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
    USERNAME = os.getenv('Username')
    PASSWORD = os.getenv('Password')
    HOSTNAME = os.getenv('Hostname')
    PORT = os.getenv('PGPort')
else:
    TOKEN = os.getenv('BETA_TOKEN')
    USERNAME = os.getenv('BETA_Username')
    PASSWORD = os.getenv('BETA_Password')
    HOSTNAME = os.getenv('BETA_Hostname')
    PORT = os.getenv('BETA_PGPort')

GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
DATABASE = os.getenv('DATABASE')


#################################################################
#################################################################
# FUNCTIONS


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# SETUP

# Set up the tracker if it does not exist
async def setup_tracker(ctx: discord.ApplicationContext, engine, bot, gm: discord.User, channel: discord.TextChannel,
                        gm_channel: discord.TextChannel, system: str):
    # Check to make sure bot has permissions in both channels
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")

    if not channel.can_send() or not gm_channel.can_send():
        await ctx.respond("Setup Failed. Ensure VirtualGM has message posting permissions in both channels.",
                          ephemeral=True)
        return False

    if system == 'Pathfinder 2e':
        g_system = 'PF2'
    elif system == "D&D 4e":
        g_system = 'D4e'
    else:
        g_system = None

    try:
        metadata = db.MetaData()
        # Build the row in Global first, because the other tables reference it
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            async with session.begin():
                guild = Global(
                    guild_id=ctx.guild.id,
                    time=0,
                    gm=str(gm.id),
                    tracker_channel=channel.id,
                    gm_tracker_channel=gm_channel.id,
                    system=g_system
                )
                session.add(guild)
                id = guild.id
            await session.commit()

        # Build the tracker, con and macro tables
        async with engine.begin() as conn:  # Call the tables directly to save a database call

            emp = await get_tracker_table(ctx, metadata, engine)
            con = await get_condition_table(ctx, metadata, engine)
            macro = await get_macro_table(ctx, metadata, engine)
            # emp = TrackerTable(ctx, metadata, id).tracker_table()
            # con = ConditionTable(ctx, metadata, id).condition_table()
            # macro = MacroTable(ctx, metadata, id).macro_table()
            await conn.run_sync(metadata.create_all)

        # Update the pinned trackers
        await set_pinned_tracker(ctx, engine, bot, channel)  # set the tracker in the player channel
        await set_pinned_tracker(ctx, engine, bot, gm_channel, gm=True)  # set up the gm_track in the GM channel
        await engine.dispose()
        return True


    except Exception as e:
        print(f'setup_tracker: {e}')
        report = ErrorReport(ctx, setup_tracker.__name__, e, bot)
        await report.report()
        await ctx.respond("Server Setup Failed. Perhaps it has already been set up?", ephemeral=True)
        return False


# Transfer gm permissions
async def set_gm(ctx: discord.ApplicationContext, new_gm: discord.User, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            guild.gm = str(new_gm.id)  # I accidentally store the GM as a string instead of an int initially
            # if I ever have to wipe the database, this should be changed
            await session.commit()
        await engine.dispose()

        return True
    except Exception as e:
        print(f'set_gm: {e}')
        report = ErrorReport(ctx, set_gm.__name__, e, bot)
        await report.report()
        return False


# delete the tracker
async def delete_tracker(ctx: discord.ApplicationContext, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        # Everything in the opposite order of creation
        metadata = db.MetaData()
        # delete each table
        emp = await get_tracker_table(ctx, metadata, engine)
        con = await get_condition_table(ctx, metadata, engine)
        macro = await get_macro_table(ctx, metadata, engine)

        async with engine.begin() as conn:
            await conn.execute(DropTable(macro, if_exists=True))
            await conn.execute(DropTable(con, if_exists=True))
            await conn.execute(DropTable(emp, if_exists=True))

        try:
            # delete the row from Global
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            async with async_session() as session:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )
                )
                )
                guild = result.scalars().one()
                await session.delete(guild)
                await session.commit()
        except Exception as e:
            print(f"guild: delete tracker: {e}")
            report = ErrorReport(ctx, "guild: delete_tracker", e, bot)
            await report.report()
        return True
    except Exception as e:
        print(f"delete tracker: {e}")
        report = ErrorReport(ctx, "delete_tracker", e, bot)
        await report.report()


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# CHARACTER MANAGEMENT

# Add a character to the database
async def add_character(ctx: discord.ApplicationContext, engine, bot, name: str, hp: int,
                        player_bool: bool, init: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

            initiative = 0
            if guild.initiative != None:
                dice = DiceRoller('')
                try:
                    # print(f"Init: {init}")
                    initiative = int(init)
                except:
                    try:
                        roll = await dice.plain_roll(init)
                        initiative = roll[1]
                        if type(initiative) != int:
                            initiative = 0
                    except:
                        initiative = 0
        if guild.system == 'PF2':
            pf2Modal = PF2AddCharacterModal(name=name, hp=hp, init=init, initiative=initiative,
                                            player=player_bool, ctx=ctx,
                                            engine=engine, bot=bot, title=name)
            await ctx.send_modal(pf2Modal)
            return True
        elif guild.system == 'D4e':
            D4eModal = D4eAddCharacterModal(name=name, hp=hp, init=init, initiative=initiative,
                                            player=player_bool, ctx=ctx,
                                            engine=engine, bot=bot, title=name)
            await ctx.send_modal(D4eModal)
            return True
        else:
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
                    temp_hp=0
                )
                session.add(tracker)
            await session.commit()

            if guild.initiative != None:
                if not await init_integrity_check(ctx, guild.initiative, guild.saved_order, engine):
                    # print(f"integrity check was false: init_pos: {guild.initiative}")
                    for pos, row in enumerate(await get_init_list(ctx, engine)):
                        await asyncio.sleep(0)
                        if row.name == guild.saved_order:
                            guild.initiative = pos
                            # print(f"integrity checked init_pos: {guild.initiative}")
                            await session.commit()

        await engine.dispose()
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'add_character: {e}')
        report = ErrorReport(ctx, add_character.__name__, e, bot)
        await report.report()
        return False


# Add a character to the database
async def edit_character(ctx: discord.ApplicationContext, engine, bot, name: str, hp: int, init: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        Tracker = await get_tracker(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == name))
            character = result.scalars().one()

            if hp != None and init != None:
                character.init_string = str(init)
                character.max_hp = hp
            elif hp != None and init == None:
                character.max_hp = hp
            elif hp == None and init != None:
                character.init_string = str(init)
            else:
                return False

            await session.commit()
        await ctx.respond(f"Character {name} edited successfully.", ephemeral=True)
        await engine.dispose()
        return True

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'add_character: {e}')
        report = ErrorReport(ctx, add_character.__name__, e, bot)
        await report.report()
        return False


async def copy_character(ctx: discord.ApplicationContext, engine, bot, name: str, new_name: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    dice = DiceRoller('')
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        # Get the table
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        # Load up the old character
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == name
            ))
            character = char_result.scalars().one()

        # If initiative is active, roll initiative
        initiative = 0
        if guild.initiative != None:
            try:
                roll = await dice.plain_roll(character.init_string)
                initiative = roll[1]
                if type(initiative) != int:
                    initiative = 0
            except:
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
                temp_hp=character.temp_hp
            )
            session.add(new_char)
        await session.commit()

        # Load the new character from the database, to get its ID
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == new_name
            ))
            new_character = char_result.scalars().one()

        async with async_session() as session:
            con_result = await session.execute(select(Condition).where(
                Condition.character_id == character.id
            ).where(Condition.visible == False))
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

        await engine.dispose()
        return True

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'add_character: {e}')
        report = ErrorReport(ctx, copy_character.__name__, e, bot)
        await report.report()
        return False


# Delete a character
async def delete_character(ctx: discord.ApplicationContext, character: str, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        # load tables
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

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

        for con in Condition_list:
            await asyncio.sleep(0)
            async with async_session() as session:
                await session.delete(con)
                await session.commit()
        for mac in Macro_list:
            await asyncio.sleep(0)
            async with async_session() as session:
                await session.delete(mac)
                await session.commit()

        async with async_session() as session:
            await session.delete(char)
            await session.commit()
        await ctx.channel.send(f"{char.name} Deleted")

        # Fix initiative position after delete:
        if guild.initiative is None:
            return True
        elif guild.saved_order == '':
            return True
        else:
            init_pos = int(guild.initiative)
            current_character = guild.saved_order
            if not await init_integrity_check(ctx, init_pos, current_character, engine):
                for pos, row in enumerate(await get_init_list(ctx, engine)):
                    if row[1] == current_character:
                        guild.initiative = pos
            await session.commit()
        await engine.dispose()
        return True
    except Exception as e:
        print(f"delete_character: {e}")
        report = ErrorReport(ctx, delete_character.__name__, e, bot)
        await report.report()
        return False


async def calculate_hp(chp, maxhp):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    hp = chp / maxhp
    if hp == 1:
        hp_string = 'Uninjured'
    elif hp >= .5:
        hp_string = 'Injured'
    elif hp >= .1:
        hp_string = 'Bloodied'
    elif chp > 0:
        hp_string = 'Critical'
    else:
        hp_string = 'Dead'

    return hp_string


async def add_thp(ctx: discord.ApplicationContext, engine, bot, name: str, amount: int):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == name
            ))
            character = char_result.scalars().one()
            character.temp_hp = character.temp_hp + amount
            await session.commit()
        await engine.dispose()
        return True
    except Exception as e:
        print(f'add_thp: {e}')
        report = ErrorReport(ctx, add_thp.__name__, e, bot)
        await report.report()
        return False


async def change_hp(ctx: discord.ApplicationContext, engine, bot, name: str, amount: int, heal: bool):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == name
            ))
            character = char_result.scalars().one()

            chp = character.current_hp
            new_hp = chp
            maxhp = character.max_hp
            thp = character.temp_hp
            new_thp = 0

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
                if new_hp == 0:
                    dead_embed = discord.Embed(title=name, description=f"{name} has reached {new_hp} HP")
                    await ctx.channel.send(embed=dead_embed)

            character.current_hp = new_hp
            character.temp_hp - new_thp
            await session.commit()
        await engine.dispose()
        return True
    except Exception as e:
        print(f'change_hp: {e}')
        report = ErrorReport(ctx, change_hp.__name__, e, bot)
        await report.report()
        return False


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# TRACKER MANAGEMENT

# Reposts new trackers in the pre-assigned channels
async def repost_trackers(ctx: discord.ApplicationContext, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            channel = bot.get_channel(guild.tracker_channel)
            gm_channel = bot.get_channel(guild.gm_tracker_channel)
            await set_pinned_tracker(ctx, engine, bot, channel)  # set the tracker in the player channel
            await set_pinned_tracker(ctx, engine, bot, gm_channel, gm=True)  # set up the gm_track in the GM channel
        await engine.dispose()
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'repost_trackers: {e}')
        report = ErrorReport(ctx, repost_trackers.__name__, e, bot)
        await report.report()
        return False


# Function sets the pinned trackers and records their position in the Global table.
async def set_pinned_tracker(ctx: discord.ApplicationContext, engine, bot, channel: discord.TextChannel, gm=False):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

            try:
                init_pos = int(guild.initiative)
            except Exception as e:
                init_pos = None
            display_string = await block_get_tracker(await get_init_list(ctx, engine), init_pos, ctx, engine,
                                                     bot, gm=gm)
            # interaction = await ctx.respond(display_string)
            interaction = await bot.get_channel(channel.id).send(display_string)
            await interaction.pin()
            if gm:
                guild.gm_tracker = interaction.id
                guild.gm_tracker_channel = channel.id
            else:
                guild.tracker = interaction.id
                guild.tracker_channel = channel.id
            await session.commit()
        await engine.dispose()
        return True
    except Exception as e:
        print(f'set_pinned_tracker: {e}')
        report = ErrorReport(ctx, set_pinned_tracker.__name__, e, bot)
        await report.report()
        return False


# Set the initiative
async def set_init(ctx: discord.ApplicationContext, bot, name: str, init: int, engine):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == name
            ))
            character = char_result.scalars().one()
            character.init = init
            await session.commit()
        return True
    except Exception as e:
        print(f'set_init: {e}')
        report = ErrorReport(ctx, set_init.__name__, e, bot)
        await report.report()
        return False


# Check to make sure that the character is in the right place in initiative
async def init_integrity_check(ctx: discord.ApplicationContext, init_pos: int, current_character: str, engine):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    init_list = await get_init_list(ctx, engine)
    if init_list[init_pos].name == current_character:
        return True
    else:
        return False


# Upgraded Advance Initiative Function to work with block initiative options
async def block_advance_initiative(ctx: discord.ApplicationContext, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")

    block_done = False
    turn_list = []
    first_pass = False

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            logging.info(f"BAI1: guild: {guild.id}")

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker))
            character = char_result.scalars().all()
            logging.info(f"BAI2: character: {character.id}")

            # print(f"guild.initiative: {guild.initiative}")
            if guild.initiative == None:
                dice = DiceRoller('')
                init_pos = -1
                guild.round = 1
                first_pass = True
                for char in character:
                    await asyncio.sleep(0)
                    if char.init == 0:
                        await asyncio.sleep(0)
                        roll = await dice.plain_roll(char.init_string)
                        await set_init(ctx, bot, char.name, roll[1], engine)
            else:
                init_pos = int(guild.initiative)

        init_list = await get_init_list(ctx, engine)
        logging.info(f"BAI3: init_list gotten")

        if guild.saved_order == '':
            current_character = init_list[0].name
        else:
            current_character = guild.saved_order
        # Record the initial to break an infinite loop
        iterations = 0
        logging.info(f"BAI4: iteration: {iterations}")

        while not block_done:
            # make sure that the current character is at the same place in initiative as it was before
            # decrement any conditions with the decrement flag

            if guild.block:  # if in block initiative, decrement conditions at the beginning of the turn
                # if its not, set the init position to the position of the current character before advancing it
                # print("Yes guild.block")
                logging.info(f"BAI5: guild.block: {guild.block}")
                if not await init_integrity_check(ctx, init_pos, current_character, engine) and not first_pass:
                    logging.info(f"BAI6: init_itegrity failied")
                    # print(f"integrity check was false: init_pos: {init_pos}")
                    for pos, row in enumerate(init_list):
                        await asyncio.sleep(0)
                        if row.name == current_character:
                            init_pos = pos
                            # print(f"integrity checked init_pos: {init_pos}")
                init_pos += 1  # increase the init position by 1
                # print(f"new init_pos: {init_pos}")
                if init_pos >= len(init_list):  # if it has reached the end, loop back to the beginning
                    init_pos = 0
                    guild.round += 1
                    if guild.timekeeping:  # if timekeeping is enable on the server
                        logging.info(f"BAI7: timekeeping")
                        # Advance time time by the number of seconds in the guild.time column. Default is 6
                        # seconds ala D&D standard
                        await advance_time(ctx, engine, bot, second=guild.time)
                        await check_cc(ctx, engine, bot)
                        logging.info(f"BAI8: cc checked")

            try:
                async with async_session() as session:
                    char_result = await session.execute(select(Tracker).where(
                        Tracker.name == current_character
                    ))
                    cur_char = char_result.scalars().one()
                    logging.info(f"BAI9: cur_char: {cur_char.id}")
            except Exception as e:
                logging.error(f'advance_initiative: {e}')
                report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
                await report.report()
                return False

            try:
                Condition = await get_condition(ctx, engine, id=guild.id)
                # con = await get_condition_table(ctx, metadata, engine)
                async with async_session() as session:
                    char_result = await session.execute(select(Condition).where(
                        Condition.character_id == cur_char.id
                    ))
                    con_list = char_result.scalars().all()
                    logging.info(f"BAI9: condition's retrieved")

                for con_row in con_list:
                    logging.info(f"BAI10: con_row: {con_row.title} {con_row.id}")
                    await asyncio.sleep(0)
                    if con_row.auto_increment and not con_row.time:  # If auto-increment and NOT time
                        if con_row.number >= 2:  # if number >= 2
                            con_row.number -= 1
                        else:
                            async with async_session() as session:
                                del_result = await session.execute(
                                    select(Condition).where(Condition.id == con_row.id))
                                del_row = del_result.scalars().one()
                                await session.delete(del_row)
                                await session.commit()
                                logging.info(f"BAI11: Condition Deleted")
                            await ctx.channel.send(f"{con_row.title} removed from {cur_char.name}")
                    elif con_row.time:  # If time is true
                        logging.info(f"BAI12: time checked")
                        time_stamp = datetime.datetime.fromtimestamp(con_row.number)  # The number is a timestamp
                        # for the expiration, not a round count
                        current_time = await get_time(ctx, engine, bot)
                        time_left = time_stamp - current_time
                        if time_left.total_seconds() <= 0:
                            async with async_session() as session:
                                del_result = await session.execute(
                                    select(Condition).where(Condition.id == con_row.id))
                                del_row = del_result.scalars().one()
                                await session.delete(del_row)
                                await session.commit()
                                logging.info(f"BAI13: Condition deleted ")
                            await ctx.channel.send(f"{con_row.title} removed from {cur_char.name}")

            except Exception as e:
                logging.error(f'block_advance_initiative: {e}')
                report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
                await report.report()

            if not guild.block:  # if not in block initiative, decrement the conditions at the end of the turn
                logging.info(f"BAI14: Not Block")
                # print("Not guild.block")
                # if its not, set the init position to the position of the current character before advancing it
                if not await init_integrity_check(ctx, init_pos, current_character, engine) and not first_pass:
                    logging.info(f"BAI15: Integrity check failed")
                    # print(f"integrity check was false: init_pos: {init_pos}")
                    for pos, row in enumerate(init_list):
                        await asyncio.sleep(0)
                        if row.name == current_character:
                            init_pos = pos
                            # print(f"integrity checked init_pos: {init_pos}")
                init_pos += 1  # increase the init position by 1
                # print(f"new init_pos: {init_pos}")
                if init_pos >= len(init_list):  # if it has reached the end, loop back to the beginning
                    init_pos = 0
                    guild.round += 1
                    if guild.timekeeping:  # if timekeeping is enable on the server
                        # Advance time time by the number of seconds in the guild.time column. Default is 6
                        # seconds ala D&D standard
                        await advance_time(ctx, engine, bot, second=guild.time)
                        await check_cc(ctx, engine, bot)
                        logging.info(f"BAI16: cc checked")

                        # block initiative loop
            # check to see if the next character is player vs npc
            # print(init_list)
            # print(f"init_pos: {init_pos}, len(init_list): {len(init_list)}")
            if init_pos >= len(init_list) - 1:
                # print(f"init_pos: {init_pos}")
                if init_list[init_pos].player != init_list[0].player:
                    block_done = True
            elif init_list[init_pos].player != init_list[init_pos + 1].player:
                block_done = True
            if not guild.block:
                block_done = True

            turn_list.append(init_list[init_pos].name)
            current_character = init_list[init_pos].name
            iterations += 1
            if iterations >= len(init_list):  # stop an infinite loop
                block_done = True

            # print(turn_list)

        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            logging.info(f"BAI17: guild updated: {guild.id}")
            # Out side while statement - for reference
            guild.initiative = init_pos  # set it
            # print(f"final init_pos: {init_pos}")
            guild.saved_order = str(init_list[init_pos].name)
            logging.info(f"BAI18: saved order: {guild.saved_order}")
            await session.commit()
            logging.info(f"BAI19: Writted")
        await engine.dispose()
        return True
    except Exception as e:
        logging.error(f"block_advance_initiative: {e}")
        report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
        await report.report()


# Returns the tracker list sorted by initiative
async def get_init_list(ctx: discord.ApplicationContext, engine):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        Tracker = await get_tracker(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker).order_by(Tracker.init.desc()).order_by(Tracker.id.desc()))
            init_list = result.scalars().all()
            logging.info(f"GIL: Init list gotten")
            # print(init_list)
        await engine.dispose()
        return init_list

    except Exception as e:
        logging.error("error in get_init_list")
        return []


async def block_get_tracker(init_list: list, selected: int, ctx: discord.ApplicationContext, engine, bot,
                            gm: bool = False):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(Global).where(
            or_(
                Global.tracker_channel == ctx.interaction.channel_id,
                Global.gm_tracker_channel == ctx.interaction.channel_id
            )
        )
        )
        guild = result.scalars().one()
        logging.info(f"BGT: Guild: {guild.id}")

        if guild.system == 'PF2':
            output_string = await PF2e.pf2_functions.pf2_get_tracker(init_list, selected, ctx, engine, bot, gm)
        elif guild.system == "D4e":
            output_string = await D4e.d4e_functions.d4e_get_tracker(init_list, selected, ctx, engine, bot, gm)
        else:
            output_string = await generic_block_get_tracker(init_list, selected, ctx, engine, bot, gm)
        return output_string


# Builds the tracker string. Updated to work with block initiative
async def generic_block_get_tracker(init_list: list, selected: int, ctx: discord.ApplicationContext, engine, bot,
                                    gm: bool = False):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    # Get the datetime
    datetime_string = ''
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(Global).where(
            or_(
                Global.tracker_channel == ctx.interaction.channel_id,
                Global.gm_tracker_channel == ctx.interaction.channel_id
            )
        )
        )
        guild = result.scalars().one()
        logging.info(f"BGT1: Guild: {guild.id}")
        if guild.block and guild.initiative != None:
            turn_list = await get_turn_list(ctx, engine, bot)
            block = True
        else:
            block = False
        round = guild.round
        logging.info(f"BGT2: round: {guild.round}")
    try:
        if await check_timekeeper(ctx, engine):
            datetime_string = f" {await output_datetime(ctx, engine, bot)}\n" \
                              f"________________________\n"
    except NoResultFound as e:
        await ctx.channel.send(
            error_not_initialized,
            delete_after=30)
        logging.info("Channel Not Set Up")
    except Exception as e:
        logging.error(f'get_tracker: {e}')
        report = ErrorReport(ctx, "get_tracker", e, bot)
        await report.report()

    try:
        Condition = await get_condition(ctx, engine, id=guild.id)
        row_data = []
        for row in init_list:
            async with async_session() as session:
                result = await session.execute(select(Condition).where(Condition.character_id == row.id))
                logging.info(f"BGT3: condition queried {row.id}")
                con = result.scalars().all()
            row_data.append({'id': row.id,
                             'name': row.name,
                             'init': row.init,
                             'player': row.player,
                             'user': row.user,
                             'chp': row.current_hp,
                             'maxhp': row.max_hp,
                             'thp': row.temp_hp,
                             'cc': con
                             })

        if round != 0:
            round_string = f"Round: {round}"
        else:
            round_string = ""

        output_string = f"```{datetime_string}" \
                        f"Initiative: {round_string}\n"
        for x, row in enumerate(row_data):
            logging.info(f"BGT4: for row x in enumerare(row_data): {x}")
            await asyncio.sleep(0)
            sel_bool = False
            selector = ''

            # don't show an init if not in combat
            if row['init'] == 0:
                init_string = ""
            else:
                init_string = f"{row['init']}"

            if block:
                for character in turn_list:
                    if row['id'] == character.id:
                        sel_bool = True
            else:
                if x == selected:
                    sel_bool = True

            # print(f"{row['name']}: x: {x}, selected: {selected}")

            if sel_bool:
                selector = '>>'
            if row['player'] or gm:
                if row['thp'] != 0:
                    string = f"{selector}  {init_string} {str(row['name']).title()}: {row['chp']}/{row['maxhp']} ({row['thp']}) Temp\n"
                else:
                    string = f"{selector}  {init_string} {str(row['name']).title()}: {row['chp']}/{row['maxhp']}\n"
            else:
                hp_string = await calculate_hp(row['chp'], row['maxhp'])
                string = f"{selector}  {init_string} {str(row['name']).title()}: {hp_string} \n"
            output_string += string

            for con_row in row['cc']:
                logging.info(f"BGT5: con_row in row[cc] {con_row.title} {con_row.id}")
                # print(con_row)
                await asyncio.sleep(0)
                if con_row.visible == True:
                    if gm or not con_row.counter:
                        if con_row.number != None and con_row.number > 0:
                            if con_row.time:
                                time_stamp = datetime.datetime.fromtimestamp(con_row.number)
                                current_time = await get_time(ctx, engine, bot)
                                time_left = time_stamp - current_time
                                days_left = time_left.days
                                processed_minutes_left = divmod(time_left.seconds, 60)[0]
                                processed_seconds_left = divmod(time_left.seconds, 60)[1]
                                if processed_seconds_left < 10:
                                    processed_seconds_left = f"0{processed_seconds_left}"
                                if days_left != 0:
                                    con_string = f"       {con_row.title}: {days_left} Days, {processed_minutes_left}:{processed_seconds_left}\n"
                                else:
                                    con_string = f"       {con_row.title}: {processed_minutes_left}:{processed_seconds_left}\n"
                            else:
                                con_string = f"       {con_row.title}: {con_row.number}\n"
                        else:
                            con_string = f"       {con_row.title}\n"

                    elif con_row.counter == True and sel_bool and row['player']:
                        con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = ''
                    output_string += con_string
                else:
                    con_string = ''
                    output_string += con_string
        output_string += f"```"
        # print(output_string)
        await engine.dispose()
        return output_string
    except Exception as e:
        logging.info(f"block_get_tracker: {e}")
        report = ErrorReport(ctx, block_get_tracker.__name__, e, bot)
        await report.report()


# Gets the locations of the pinned trackers, then updates them with the newest tracker
async def update_pinned_tracker(ctx: discord.ApplicationContext, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        try:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            logging.info(f"UPT1: Guild: {guild.id}")

            tracker = guild.tracker
            tracker_channel = guild.tracker_channel
            gm_tracker = guild.gm_tracker
            gm_tracker_channel = guild.gm_tracker_channel

            # Update the tracker
            if tracker is not None:
                tracker_display_string = await block_get_tracker(await get_init_list(ctx, engine), guild.initiative,
                                                                 ctx, engine, bot)
                channel = bot.get_channel(tracker_channel)
                message = await channel.fetch_message(tracker)
                await message.edit(tracker_display_string)
                logging.info(f"UPT2: tracker updated")

            # Update the GM tracker
            if gm_tracker is not None:
                gm_tracker_display_string = await block_get_tracker(await get_init_list(ctx, engine), guild.initiative,
                                                                    ctx, engine, bot, gm=True)
                gm_channel = bot.get_channel(gm_tracker_channel)
                gm_message = await gm_channel.fetch_message(gm_tracker)
                await gm_message.edit(gm_tracker_display_string)
                logging.info(f"UPT3: gm tracker updated")
        except NoResultFound as e:
            await ctx.channel.send(
                error_not_initialized,
                delete_after=30)
        except Exception as e:
            logging.error(f'update_pinned_tracker: {e}')
            report = ErrorReport(ctx, update_pinned_tracker.__name__, e, bot)
            await report.report()


async def block_post_init(ctx: discord.ApplicationContext, engine, bot: discord.Bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    # Query the initiative position for the tracker and post it
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            logging.info(f"BPI1: guild: {guild.id}")
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        if guild.block:
            turn_list = await get_turn_list(ctx, engine, bot)
            block = True
            # print(f"block_post_init: \n {turn_list}")
        else:
            block = False

        init_list = await get_init_list(ctx, engine)
        tracker_string = await block_get_tracker(init_list, guild.initiative, ctx, engine, bot)
        try:
            logging.info(f"BPI2")
            ping_string = ''
            if block:
                for character in turn_list:
                    await asyncio.sleep(0)
                    user = bot.get_user(character.user)
                    ping_string += f"{user.mention}, it's your turn.\n"
            else:
                user = bot.get_user(init_list[guild.initiative].user)
                ping_string += f"{user.mention}, it's your turn.\n"
        except Exception as e:
            # print(f'post_init: {e}')
            ping_string = ''

        # Check for systems:
        if guild.system == 'D4e':
            logging.info(f"BPI3: d4e")
            view = discord.ui.View()
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == init_list[guild.initiative].name))
                char = result.scalars().one()
            async with async_session() as session:
                result = await session.execute(select(Condition)
                                               .where(Condition.character_id == char.id)
                                               .where(Condition.flex == True))
                conditions = result.scalars().all()
            for con in conditions:
                new_button = D4e.d4e_functions.D4eConditionButton(
                    con,
                    ctx, engine, bot,
                    char,
                )
                view.add_item(new_button)

            if ctx.channel.id == guild.tracker_channel:
                await ctx.send_followup(f"{tracker_string}\n"
                                        f"{ping_string}", view=view)
            else:
                await bot.get_channel(guild.tracker_channel).send(f"{tracker_string}\n"
                                                                  f"{ping_string}", view=view,)
                await ctx.send_followup("Initiative Advanced.")
                logging.info(f"BPI4")
        else:
            # Always post the tracker to the player channel
            if ctx.channel.id == guild.tracker_channel:
                await ctx.send_followup(f"{tracker_string}\n"
                                        f"{ping_string}")
            else:
                await bot.get_channel(guild.tracker_channel).send(f"{tracker_string}\n"
                                                                  f"{ping_string}")
                await ctx.send_followup("Initiative Advanced.")
                logging.info(f"BPI5")
        await engine.dispose()
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
    except Exception as e:
        logging.error(f"block_post_init: {e}")
        report = ErrorReport(ctx, block_post_init.__name__, e, bot)
        await report.report()


# Note: Works backwards
async def get_turn_list(ctx: discord.ApplicationContext, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    turn_list = []
    block_done = False
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            logging.info(f"GTL1: guild: {guild.id}")
            iteration = 0
            init_pos = guild.initiative
            # print(f"init_pos: {init_pos}")
            # print(init_pos)
            init_list = await get_init_list(ctx, engine)
            length = len(init_list)
            while not block_done:
                turn_list.append(init_list[init_pos])
                # print(f"init_pos: {init_pos}, turn_list: {turn_list}")
                player_status = init_list[init_pos].player
                if init_pos == 0:
                    if player_status != init_list[length - 1].player:
                        block_done = True
                else:
                    if player_status != init_list[init_pos - 1].player:
                        block_done = True

                init_pos -= 1
                if init_pos < 0:
                    if guild.round != 1:  # Don't loop back to the end on the first round
                        init_pos = length - 1
                    else:
                        block_done = True
                iteration += 1
                if iteration >= length:
                    block_done = True
            await engine.dispose()
            logging.info(f"GTL2 {turn_list }")
            return turn_list
    except Exception as e:
        print(f'get_turn_list: {e}')
        report = ErrorReport(ctx, get_turn_list.__name__, e, bot)
        await report.report()
        return False


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# COUNTER/CONDITION MANAGEMENT

async def set_cc(ctx: discord.ApplicationContext, engine, character: str, title: str, counter: bool, number: int,
                 unit: str, auto_decrement: bool, bot, flex: bool = False, ):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    # Get the Character's data

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'set_cc: {e}')
        report = ErrorReport(ctx, set_cc.__name__, e, bot)
        await report.report()
        return False

    try:
        if not guild.timekeeping or unit == 'Round':
            async with session.begin():
                condition = Condition(
                    character_id=character.id,
                    title=title,
                    number=number,
                    counter=counter,
                    auto_increment=auto_decrement,
                    time=False,
                    flex=flex
                )
                session.add(condition)
            await session.commit()

            await update_pinned_tracker(ctx, engine, bot)
            await engine.dispose()
            return True

        else:
            current_time = await get_time(ctx, engine, bot)
            if unit == 'Minute':
                end_time = current_time + datetime.timedelta(minutes=number)
            elif unit == 'Hour':
                end_time = current_time + datetime.timedelta(hours=number)
            else:
                end_time = current_time + datetime.timedelta(days=number)

            timestamp = end_time.timestamp()

            async with session.begin():
                condition = Condition(
                    character_id=character.id,
                    title=title,
                    number=timestamp,
                    counter=counter,
                    auto_increment=True,
                    time=True
                )
                session.add(condition)
            await session.commit()
            await update_pinned_tracker(ctx, engine, bot)
            await engine.dispose()
            return True

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'set_cc: {e}')
        report = ErrorReport(ctx, set_cc.__name__, e, bot)
        await report.report()
        return False


async def edit_cc(ctx: discord.ApplicationContext, engine, character: str, condition: str, value: int, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        Tracker = await get_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'edit_cc: {e}')
        report = ErrorReport(ctx, edit_cc.__name__, e, bot)
        await report.report()
        return False

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == character.id).where(Condition.title == condition))
            condition = result.scalars().one()

            if condition.time:
                await ctx.send_followup("Unable to edit time based conditions. Try again in a future update.",
                                        ephemeral=True)
                return False
            else:
                condition.number = value
                await session.commit()
        await update_pinned_tracker(ctx, engine, bot)
        await engine.dispose()
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'edit_cc: {e}')
        report = ErrorReport(ctx, edit_cc.__name__, e, bot)
        await report.report()
        return False


async def delete_cc(ctx: discord.ApplicationContext, engine, character: str, condition, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        Tracker = await get_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'delete_cc: {e}')
        report = ErrorReport(ctx, delete_cc.__name__, e, bot)
        await report.report()
        return False

    try:
        async with async_session() as session:
            result = await session.execute(select(Condition)
                                           .where(Condition.character_id == character.id)
                                           .where(Condition.visible == True)
                                           .where(Condition.title == condition))
            con_list = result.scalars().all()

        for con in con_list:
            await asyncio.sleep(0)
            async with async_session() as session:
                await session.delete(con)
                await session.commit()

        await update_pinned_tracker(ctx, engine, bot)
        await engine.dispose()
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'delete_cc: {e}')
        report = ErrorReport(ctx, delete_cc.__name__, e, bot)
        await report.report()
        return False


async def get_cc(ctx: discord.ApplicationContext, engine, bot, character: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    Tracker = await get_tracker(ctx, engine)
    Condition = await get_condition(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'get_cc: {e}')
        report = ErrorReport(ctx, get_cc.__name__, e, bot)
        await report.report()

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == character.id).where(Condition.counter == True))
            counters = result.scalars().all()

        await engine.dispose()
        return counters
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'get_cc: {e}')
        report = ErrorReport(ctx, get_cc.__name__, e, bot)
        await report.report()


# Check to see if any time duration conditions have expired.
# Intended to be called when time is advanced
async def check_cc(ctx: discord.ApplicationContext, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    current_time = await get_time(ctx, engine, bot)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    Tracker = await get_tracker(ctx, engine)
    Condition = await get_condition(ctx, engine)

    async with async_session() as session:
        result = await session.execute(select(Condition).where(Condition.time == True))
        con_list = result.scalars().all()

    for row in con_list:
        await asyncio.sleep(0)
        time_stamp = datetime.datetime.fromtimestamp(row.number)
        time_left = time_stamp - current_time
        if time_left.total_seconds() <= 0:
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == row.character_id))
                character = result.scalars().one()
            async  with async_session() as session:
                await session.delete(row)
                await session.commit()
            await ctx.channel.send(f"{row.title} removed from {character.name}")
    await engine.dispose()


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# UTILITY FUNCTIONS

# Checks to see if the user of the slash command is the GM, returns a boolean
async def gm_check(ctx, engine):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            if int(guild.gm) != int(ctx.interaction.user.id):
                return False
            else:
                return True
    except Exception as e:
        return False


# checks to see if the player is the ower of the character
# possibly depreciated due to auto-complete
async def player_check(ctx: discord.ApplicationContext, engine, bot, character: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        Tracker = await get_tracker(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == character))
            character = char_result.scalars().one()
        return character

    except Exception as e:
        print(f'player_check: {e}')
        report = ErrorReport(ctx, player_check.__name__, e, bot)
        await report.report()


#############################################################################
#############################################################################
# Specific character modals

class PF2AddCharacterModal(discord.ui.Modal):
    def __init__(self, name: str, hp: int, init: str, initiative, player, ctx, engine, bot, *args, **kwargs):
        self.name = name
        self.hp = hp
        self.init = init
        self.initiative = initiative
        self.player = player
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
        super().__init__(
            discord.ui.InputText(
                label="AC",
                placeholder="Armor Class",
            ),
            discord.ui.InputText(
                label="Fort",
                placeholder="Fortitude",
            ),
            discord.ui.InputText(
                label="Reflex",
                placeholder="Reflex",
            ),
            discord.ui.InputText(
                label="Will",
                placeholder="Will",
            ),
            discord.ui.InputText(
                label="Class / Spell DC",
                placeholder="DC",
            ), *args, **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == self.ctx.interaction.channel_id,
                    Global.gm_tracker_channel == self.ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

        embed = discord.Embed(
            title="Character Created (PF2)",
            fields=[
                discord.EmbedField(
                    name="Name: ", value=self.name, inline=True
                ),
                discord.EmbedField(
                    name="HP: ", value=f"{self.hp}", inline=True
                ),
                discord.EmbedField(
                    name="AC: ", value=self.children[0].value, inline=True
                ),
                discord.EmbedField(
                    name="Fort: ", value=self.children[1].value, inline=True
                ),
                discord.EmbedField(
                    name="Reflex: ", value=self.children[2].value, inline=True
                ),
                discord.EmbedField(
                    name="Will: ", value=self.children[3].value, inline=True
                ),
                discord.EmbedField(
                    name="Class/Spell DC: ", value=self.children[4].value, inline=True
                ),
                discord.EmbedField(
                    name="Initiative: ", value=self.init, inline=True
                ),
            ],
            color=discord.Color.dark_gold(),
        )

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            Tracker = await get_tracker(self.ctx, self.engine, id=guild.id)
            async with session.begin():
                tracker = Tracker(
                    name=self.name,
                    init_string=self.init,
                    init=self.initiative,
                    player=self.player,
                    user=self.ctx.user.id,
                    current_hp=self.hp,
                    max_hp=self.hp,
                    temp_hp=0
                )
                session.add(tracker)
            await session.commit()

        Condition = await get_condition(self.ctx, self.engine, id=guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
            character = char_result.scalars().one()

        async with session.begin():
            session.add(Condition(
                character_id=character.id,
                title='AC',
                number=int(self.children[0].value),
                counter=True,
                visible=False))
            session.add(Condition(
                character_id=character.id,
                title='Fort',
                number=int(self.children[1].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Reflex',
                number=int(self.children[2].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Will',
                number=int(self.children[3].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='DC',
                number=int(self.children[4].value),
                counter=True,
                visible=False
            ))
            await session.commit()

        async with session.begin():
            if guild.initiative != None:
                if not await init_integrity_check(self.ctx, guild.initiative, guild.saved_order, self.engine):
                    # print(f"integrity check was false: init_pos: {guild.initiative}")
                    for pos, row in enumerate(await get_init_list(self.ctx, self.engine)):
                        await asyncio.sleep(0)
                        if row.name == guild.saved_order:
                            guild.initiative = pos
                            # print(f"integrity checked init_pos: {guild.initiative}")
                            await session.commit()

        # await update_pinned_tracker(self.ctx, self.engine, self.bot)
        print('Tracker Updated')
        await interaction.response.send_message(embeds=[embed])

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        print(error)


# D&D 4e Specific
class D4eAddCharacterModal(discord.ui.Modal):
    def __init__(self, name: str, hp: int, init: str, initiative, player, ctx, engine, bot, *args, **kwargs):
        self.name = name
        self.hp = hp
        self.init = init
        self.initiative = initiative
        self.player = player
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
        super().__init__(
            discord.ui.InputText(
                label="AC",
                placeholder="Armor Class",
            ),
            discord.ui.InputText(
                label="Fort",
                placeholder="Fortitude",
            ),
            discord.ui.InputText(
                label="Reflex",
                placeholder="Reflex",
            ),
            discord.ui.InputText(
                label="Will",
                placeholder="Will",
            ), *args, **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == self.ctx.interaction.channel_id,
                    Global.gm_tracker_channel == self.ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

        embed = discord.Embed(
            title="Character Created (D&D 4e)",
            fields=[
                discord.EmbedField(
                    name="Name: ", value=self.name, inline=True
                ),
                discord.EmbedField(
                    name="HP: ", value=f"{self.hp}", inline=True
                ),
                discord.EmbedField(
                    name="AC: ", value=self.children[0].value, inline=True
                ),
                discord.EmbedField(
                    name="Fort: ", value=self.children[1].value, inline=True
                ),
                discord.EmbedField(
                    name="Reflex: ", value=self.children[2].value, inline=True
                ),
                discord.EmbedField(
                    name="Will: ", value=self.children[3].value, inline=True
                ),
                discord.EmbedField(
                    name="Initiative: ", value=self.init, inline=True
                ),
            ],
            color=discord.Color.dark_gold(),
        )

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            Tracker = await get_tracker(self.ctx, self.engine, id=guild.id)
            async with session.begin():
                tracker = Tracker(
                    name=self.name,
                    init_string=self.init,
                    init=self.initiative,
                    player=self.player,
                    user=self.ctx.user.id,
                    current_hp=self.hp,
                    max_hp=self.hp,
                    temp_hp=0
                )
                session.add(tracker)
            await session.commit()

        Condition = await get_condition(self.ctx, self.engine, id=guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
            character = char_result.scalars().one()

        async with session.begin():
            session.add(Condition(
                character_id=character.id,
                title='AC',
                number=int(self.children[0].value),
                counter=True,
                visible=False))
            session.add(Condition(
                character_id=character.id,
                title='Fort',
                number=int(self.children[1].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Reflex',
                number=int(self.children[2].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Will',
                number=int(self.children[3].value),
                counter=True,
                visible=False
            ))
            await session.commit()

        async with session.begin():
            if guild.initiative != None:
                if not await init_integrity_check(self.ctx, guild.initiative, guild.saved_order, self.engine):
                    # print(f"integrity check was false: init_pos: {guild.initiative}")
                    for pos, row in enumerate(await get_init_list(self.ctx, self.engine)):
                        await asyncio.sleep(0)
                        if row.name == guild.saved_order:
                            guild.initiative = pos
                            # print(f"integrity checked init_pos: {guild.initiative}")
                            await session.commit()

        # await update_pinned_tracker(self.ctx, self.engine, self.bot)
        print('Tracker Updated')
        await interaction.response.send_message(embeds=[embed])

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        print(error)


#############################################################################
#############################################################################
# SLASH COMMANDS
# The Initiative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.lock = asyncio.Lock()
        self.update_status.start()
        self.check_latency.start()
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @tasks.loop(seconds=30)
    async def check_latency(self):
        logging.info(f"{self.bot.latency}: {datetime.datetime.now()}")

    # Update the bot's status periodically
    @tasks.loop(minutes=1)
    async def update_status(self):
        async with self.async_session() as session:
            guild = await session.execute(select(Global))
            result = guild.scalars().all()
            count = len(result)
        async with self.lock:
            await self.bot.change_presence(activity=discord.Game(name=f"ttRPGs in {count} tables across the "
                                                                      f"digital universe."))

    # Don't start the loop unti the bot is ready
    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Autocomplete Methods

    # Autocomplete to give the full character list
    async def character_select(self, ctx: discord.AutocompleteContext):
        character_list = []

        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(ctx, self.engine)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker))
                character = char_result.scalars().all()
                for char in character:
                    await asyncio.sleep(0)
                    character_list.append(char.name)
                await self.engine.dispose()
                return character_list

        except Exception as e:
            print(f'character_select: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return []

    # Autocomplete to return the list of character the user owns, or all if the user is the GM
    async def character_select_gm(self, ctx: discord.AutocompleteContext):
        character_list = []

        gm_status = await gm_check(ctx, self.engine)

        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(ctx, self.engine)

            async with async_session() as session:
                if gm_status:
                    char_result = await session.execute(select(Tracker))
                else:
                    char_result = await session.execute(select(Tracker).where(Tracker.user == ctx.interaction.user.id))
                character = char_result.scalars().all()
                for char in character:
                    await asyncio.sleep(0)
                    character_list.append(char.name)
                await self.engine.dispose()
                return character_list

        except Exception as e:
            print(f'character_select_gm: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return []

    # Autocomplete to return only non-player characters
    async def npc_select(self, ctx: discord.AutocompleteContext):
        character_list = []

        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(ctx, self.engine)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.player == False))
                character = char_result.scalars().all()
                for char in character:
                    await asyncio.sleep(0)
                    character_list.append(char.name)
                await self.engine.dispose()
                return character_list

        except Exception as e:
            print(f'character_select: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return []

    async def cc_select(self, ctx: discord.AutocompleteContext):
        character = ctx.options['character']

        con_list = []
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(ctx, self.engine)
            Condition = await get_condition(ctx, self.engine)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(
                    Tracker.name == character
                ))
                char = char_result.scalars().one()
            async with async_session() as session:
                con_result = await session.execute(select(Condition).where(
                    Condition.character_id == char.id
                ))
                condition = con_result.scalars().all()
            for cond in condition:
                con_list.append(cond.title)
            await self.engine.dispose()
            return con_list

        except Exception as e:
            print(f'cc_select: {e}')
            report = ErrorReport(ctx, self.cc_select.__name__, e, self.bot)
            await report.report()
            return []

    async def time_check_ac(self, ctx: discord.AutocompleteContext):
        if await check_timekeeper(ctx, self.engine):
            return ['Round', 'Minute', 'Hour', 'Day']
        else:
            return ['Round']

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Slash commands

    i = SlashCommandGroup("i", "Initiative Tracker")
    char = SlashCommandGroup("char", "Character Commands")
    cc = SlashCommandGroup("cc", "Conditions and Counters")

    @i.command(description="D&D 4e auto save")
    # @commands.slash_command(name="d4e_save", guild_ids=[GUILD])
    @option('character', description='Character Attacking', autocomplete=character_select_gm)
    @option('condition', description="Select Condition", autocomplete=cc_select)
    async def save(self, ctx: discord.ApplicationContext, character: str, condition: str, modifier: str = ''):
        await ctx.response.defer()
        async with self.async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            if guild.system == "D4e":
                output_string = D4e.d4e_functions.save(ctx, self.engine, self.bot, character, condition, modifier)

                await ctx.send_followup(output_string)
            else:
                await ctx.send_followup("No system set, command inactive.")
                return

    @char.command(description="Add PC on NPC",
                  # guild_ids=[GUILD]
                  )
    @option('name', description="Character Name", input_type=str)
    @option('hp', description='Total HP', input_type=int)
    @option('player', choices=['player', 'npc'], input_type=str)
    @option('initiative', description="Initiative Roll (XdY+Z)", required=True, input_type=str)
    async def add(self, ctx: discord.ApplicationContext, name: str, hp: int,
                  player: str, initiative: str):
        # await ctx.response.defer(ephemeral=True)
        response = False
        player_bool = False
        if player == 'player':
            player_bool = True
        elif player == 'npc':
            player_bool = False

        response = await add_character(ctx, self.engine, self.bot, name, hp, player_bool, initiative)
        if response:
            await ctx.respond(f"Character {name} added successfully.", ephemeral=True)
        else:
            await ctx.respond(f"Error Adding Character", ephemeral=True)

        await update_pinned_tracker(ctx, self.engine, self.bot)

    @char.command(description="Edit PC on NPC")
    @option('name', description="Character Name", input_type=str, autocomplete=character_select_gm, )
    @option('hp', description='Total HP', input_type=int, required=False)
    @option('initiative', description="Initiative Roll (XdY+Z)", required=False, input_type=str)
    async def edit(self, ctx: discord.ApplicationContext, name: str, hp: int, initiative: str):
        response = False

        response = await edit_character(ctx, self.engine, self.bot, name, hp, initiative)
        if not response:
            await ctx.respond(f"Error Editing Character", ephemeral=True)

        await update_pinned_tracker(ctx, self.engine, self.bot)

    @char.command(description="Duplicate Character")
    @option('name', description="Character Name", input_type=str, autocomplete=character_select_gm, )
    @option('new_name', description='Name for the new NPC', input_type=str, required=True)
    async def copy(self, ctx: discord.ApplicationContext, name: str, new_name: str):
        await ctx.response.defer(ephemeral=True)
        response = False
        response = await copy_character(ctx, self.engine, self.bot, name, new_name)
        if response:
            await ctx.send_followup(f"{new_name} Created", ephemeral=True)
        else:
            await ctx.send_followup(f"Error Copying Character", ephemeral=True)

        await update_pinned_tracker(ctx, self.engine, self.bot)

    @char.command(description="Delete NPC")
    @option('name', description="Character Name", input_type=str, autocomplete=npc_select, )
    async def delete(self, ctx: discord.ApplicationContext, name: str):
        await ctx.response.defer(ephemeral=True)

        async with self.async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

        if name == guild.saved_order:
            await ctx.send_followup(
                f"Please wait until {name} is not the active character in initiative before "
                f"deleting it.", ephemeral=True)
        else:
            result = await delete_character(ctx, name, self.engine, self.bot)
            if result:
                await ctx.send_followup(f'{name} deleted', ephemeral=True)
                await update_pinned_tracker(ctx, self.engine, self.bot)
            else:
                await ctx.send_followup('Delete Operation Failed', ephemeral=True)
        await self.engine.dispose()

    @i.command(description="Manage Initiative",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    @option('mode', choices=['start', 'stop', 'delete character'], required=True)
    @option('character', description='Character to delete', required=False)
    async def manage(self, ctx: discord.ApplicationContext, mode: str, character: str = ''):
        try:
            async with self.async_session() as session:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )
                )
                )
                guild = result.scalars().one()
            if not await gm_check(ctx, self.engine):
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            else:
                if mode == 'start':
                    await ctx.response.defer()
                    await block_advance_initiative(ctx, self.engine, self.bot)
                    await block_post_init(ctx, self.engine, self.bot)
                    await update_pinned_tracker(ctx, self.engine, self.bot)
                    # await ctx.respond('Initiative Started', ephemeral=True)
                elif mode == 'stop':  # Stop initiative
                    await ctx.response.defer()
                    # Reset variables to the neutral state
                    async with self.async_session() as session:
                        result = await session.execute(select(Global).where(
                            or_(
                                Global.tracker_channel == ctx.interaction.channel_id,
                                Global.gm_tracker_channel == ctx.interaction.channel_id
                            )
                        )
                        )
                        guild = result.scalars().one()
                        guild.initiative = None
                        guild.saved_order = ''
                        guild.round = 0
                        await session.commit()
                    metadata = db.MetaData()
                    # Update the tables
                    Tracker = await get_tracker(ctx, self.engine, id=guild.id)
                    Condition = await get_condition(ctx, self.engine, id=guild.id)

                    # tracker cleanup
                    # Delete condition with round timers
                    async  with self.async_session() as session:
                        result = await session.execute(
                            select(Condition).where(Condition.auto_increment == True).where(Condition.time == False))
                        con_del_list = result.scalars().all()
                    for con in con_del_list:
                        await asyncio.sleep(0)
                        async  with self.async_session() as session:
                            await session.delete(con)
                            await session.commit

                    # Delete any dead NPCs
                    async with self.async_session() as session:
                        result = await session.execute(
                            select(Tracker).where(Tracker.current_hp <= 0).where(Tracker.player == False))
                        delete_list = result.scalars().all()
                    for npc in delete_list:
                        await delete_character(ctx, npc.name, self.engine, self.bot)

                    # Set all initiatives to 0
                    async with self.async_session() as session:
                        result = await session.execute(select(Tracker))
                        tracker_list = result.scalars().all()
                        for item in tracker_list:
                            item.init = 0
                        await session.commit()
                    await update_pinned_tracker(ctx, self.engine, self.bot)
                    await ctx.send_followup("Initiative Ended.")
                elif mode == 'delete character':
                    if character == guild.saved_order:
                        await ctx.respond(
                            f"Please wait until {character} is not the active character in initiative before "
                            f"deleting it.", ephemeral=True)
                    else:
                        await ctx.response.defer()
                        result = await delete_character(ctx, character, self.engine, self.bot)
                        if result:
                            await ctx.send_followup(f'{character} deleted', ephemeral=True)
                            await update_pinned_tracker(ctx, self.engine, self.bot)
                        else:
                            await ctx.send_followup('Delete Operation Failed')
            await self.engine.dispose()
        except NoResultFound as e:
            await ctx.respond(
                error_not_initialized,
                ephemeral=True)
            return False
        except IndexError as e:
            await ctx.respond("Ensure that you have added characters to the initiative list.")
        except Exception as e:
            await ctx.respond("Failed")

    @i.command(description="Advance Initiative",
               # guild_ids=[GUILD]
               )
    async def next(self, ctx: discord.ApplicationContext):
        try:
            await ctx.response.defer()
            # Advance Init and Display
            await block_advance_initiative(ctx, self.engine, self.bot)  # Advance the init

            # Query the initiative position for the tracker and post it
            await block_post_init(ctx, self.engine, self.bot)
            await update_pinned_tracker(ctx, self.engine, self.bot)  # update the pinned tracker

        except NoResultFound as e:
            await ctx.respond(error_not_initialized, ephemeral=True)
        except Exception as e:
            print(f"/i next: {e}")
            report = ErrorReport(ctx, "slash command /i next", e, self.bot)
            await report.report()

    @i.command(description="Set Init (Number or XdY+Z)",
               # guild_ids=[GUILD]
               )
    @option("character", description="Character to select", autocomplete=character_select_gm, )
    async def init(self, ctx: discord.ApplicationContext, character: str, init: str):
        async with self.async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

            if character == guild.saved_order:
                await ctx.respond(f"Please wait until {character} is not the active character in initiative before "
                                  f"resetting its initiative.", ephemeral=True)
            else:
                dice = DiceRoller('')
                try:
                    # print(f"Init: {init}")
                    initiative = int(init)
                    success = await set_init(ctx, self.bot, character, initiative, self.engine)
                    if success:
                        await ctx.respond(f"Initiative set to {initiative} for {character}")
                    else:
                        await ctx.respond("Failed to set initiative.", ephemeral=True)
                except:
                    roll = await dice.plain_roll(init)
                    success = await set_init(ctx, self.bot, character, roll[1], self.engine)
                    if success:
                        await ctx.respond(f"Initiative set to {roll[0]} = {roll[1]} for {character}")
                    else:
                        await ctx.respond("Failed to set initiative.", ephemeral=True)
            await update_pinned_tracker(ctx, self.engine, self.bot)
        await self.engine.dispose()

    @i.command(description="Heal, Damage or add Temp HP",
               # guild_ids=[GUILD]
               )
    @option('name', description="Character Name", autocomplete=character_select)
    @option('mode', choices=['Damage', 'Heal', "Temporary HP"])
    async def hp(self, ctx: discord.ApplicationContext, name: str, mode: str, amount: int):
        response = False
        if mode == 'Heal':
            response = await change_hp(ctx, self.engine, self.bot, name, amount, True)
            if response:
                await ctx.respond(f"{name} healed for {amount}.")
        elif mode == 'Damage':
            response = await change_hp(ctx, self.engine, self.bot, name, amount, False)
            if response:
                await ctx.respond(f"{name} damaged for {amount}.")
        elif mode == 'Temporary HP':
            response = await add_thp(ctx, self.engine, self.bot, name, amount)
            if response:
                await ctx.respond(f"{amount} Temporary HP added to {name}.")
        if not response:
            await ctx.respond("Failed", ephemeral=True)
        await update_pinned_tracker(ctx, self.engine, self.bot)

    @cc.command(description="Add conditions and counters",
                # guild_ids=[GUILD]
                )
    @option("character", description="Character to select", autocomplete=character_select)
    @option('type', choices=['Condition', 'Counter'])
    @option('auto', description="Auto Decrement", choices=['Auto Decrement', 'Static'])
    @option('unit', autocomplete=time_check_ac)
    @option('flex', autocomplete=discord.utils.basic_autocomplete(["True", "False"]))
    async def new(self, ctx: discord.ApplicationContext, character: str, title: str, type: str, number: int = None,
                  unit: str = "Round",
                  auto: str = 'Static',
                  flex: str = "False"):
        await ctx.response.defer(ephemeral=True)
        if flex == 'False':
            flex_bool = False
        else:
            flex_bool = True

        if type == "Condition":
            counter_bool = False
        else:
            counter_bool = True
        if auto == 'Auto Decrement':
            auto_bool = True
        else:
            auto_bool = False

        response = await set_cc(ctx, self.engine, character, title, counter_bool, number, unit, auto_bool, self.bot,
                                flex=flex_bool)
        if response:
            await ctx.send_followup("Success", ephemeral=True)
        else:
            await ctx.send_followup("Failure", ephemeral=True)

    @cc.command(description="Edit or remove conditions and counters",
                # guild_ids=[GUILD]
                )
    @option('mode', choices=['edit', 'delete'])
    @option("character", description="Character to select", autocomplete=character_select)
    @option("condition", description="Condition", autocomplete=cc_select)
    async def edit(self, ctx: discord.ApplicationContext, mode: str, character: str, condition: str,
                   new_value: int = 0):
        result = False
        await ctx.response.defer(ephemeral=True)
        if mode == 'delete':
            result = await delete_cc(ctx, self.engine, character, condition, self.bot)
            if result:
                await ctx.send_followup(f"{condition} on {character} deleted.", ephemeral=True)
        elif mode == 'edit':
            result = await edit_cc(ctx, self.engine, character, condition, new_value, self.bot)
            if result:
                await ctx.send_followup(f"{condition} on {character} updated.", ephemeral=True)
        else:
            await ctx.send_followup("Invalid Input", ephemeral=True)

        if not result:
            await ctx.send_followup("Failed", ephemeral=True)

    @cc.command(description="Show Custom Counters")
    @option("character", description="Character to select", autocomplete=character_select_gm)
    async def show(self, ctx: discord.ApplicationContext, character: str):
        await ctx.response.defer(ephemeral=True)
        try:
            if not await player_check(ctx, self.engine, self.bot, character) and not await gm_check(ctx, self.engine):
                await ctx.send_followup(f'Viewing NPC counters is restricted to the GM only.', ephemeral=True)
            else:
                cc_list = await get_cc(ctx, self.engine, self.bot, character)
                output_string = f'```{character}:\n'
                for row in cc_list:
                    await asyncio.sleep(0)
                    counter_string = f'{row.title}: {row.number}'
                    output_string += counter_string
                    output_string += '\n'
                output_string += "```"
                await ctx.send_followup(output_string, ephemeral=True)
        except Exception as e:
            print(f'cc_show: {e}')
            await ctx.send_followup(f'Failed: Ensure that {character} is a valid character', ephemeral=True)


def setup(bot):
    bot.add_cog(InitiativeCog(bot))
