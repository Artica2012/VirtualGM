# initiative.py
# Initiative Tracker Module
import datetime
import os

# imports
import discord
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import sqlalchemy as db
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_, func
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.sql.ddl import DropTable
import PF2e.pf2_functions

from database_models import Global, Base, TrackerTable, ConditionTable, MacroTable
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
    if not channel.can_send() or not gm_channel.can_send():
        await ctx.respond("Setup Failed. Ensure VirtualGM has message posting permissions in both channels.",
                          ephemeral=True)
        return False

    if system == 'Pathfinder 2e':
        g_system = 'PF2'
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
    metadata = db.MetaData()

    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        con = await get_condition_table(ctx, metadata, engine)
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
                await ctx.send_modal(PF2AddCharacterModal(name=name, hp=hp, init=init, initiative=initiative,
                                                          player=player_bool, ctx=ctx,
                                                          emp=emp, con=con, engine=engine, bot=bot, title=name))
            else:
                stmt = emp.insert().values(
                    name=name,
                    init_string=init,
                    init=initiative,
                    player=player_bool,
                    user=ctx.user.id,
                    current_hp=hp,
                    max_hp=hp,
                    temp_hp=0
                )
                async with engine.begin() as conn:
                    result = await conn.execute(stmt)
                    # conn.commit()
            await ctx.send_followup(f"Character {name} added successfully.", ephemeral=True)

            if guild.initiative != None:
                if not await init_integrity_check(ctx, guild.initiative, guild.saved_order, engine):
                    # print(f"integrity check was false: init_pos: {guild.initiative}")
                    for pos, row in enumerate(await get_init_list(ctx, engine)):
                        if row[1] == guild.saved_order:
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
    metadata = db.MetaData()
    dice = DiceRoller('')

    try:
        emp = await get_tracker_table(ctx, metadata, engine)

        if hp != None and init != None:
            stmt = emp.update().where(emp.c.name == name).values(
                init_string=str(init),
                max_hp=hp,
            )
        elif hp != None and init == None:
            stmt = emp.update().where(emp.c.name == name).values(
                max_hp=hp,
            )
        elif hp == None and init != None:
            stmt = emp.update().where(emp.c.name == name).values(
                init_string=str(init),
            )
        else:
            return False

        async with engine.begin() as conn:
            result = await conn.execute(stmt)
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
    metadata = db.MetaData()
    dice = DiceRoller('')
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        con = await get_condition_table(ctx, metadata, engine)
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

        old_char_stmt = emp.select().where(emp.c.name == name)
        async with engine.begin() as conn:
            for row in await conn.execute(old_char_stmt):
                initiative = 0
                if guild.initiative != None:
                    try:
                        roll = await dice.plain_roll(row[8])
                        initiative = roll[1]
                        if type(initiative) != int:
                            initiative = 0
                    except:
                        initiative = 0
                new_char_stmt = emp.insert().values(
                    name=new_name,
                    init_string=row[8],
                    init=initiative,
                    player=row[3],
                    user=row[4],
                    current_hp=row[5],
                    max_hp=row[6],
                    temp_hp=row[7]
                )
                old_char_id = row[0]  # Save the ID of the old character

                await conn.execute(new_char_stmt)  # Copy the character with a new name and ID
                id_stmt = emp.select().where(emp.c.name == new_name)
                new_char_id = None  # Get the ID of the new character
                for id_row in await conn.execute(id_stmt):
                    new_char_id = id_row[0]

                # copy over the invisible conditions
                con_stmt = con.select().where(con.c.character_id == old_char_id).where(con.c.visible == False)
                old_con_list = []
                for con_row in await conn.execute(con_stmt):
                    add_con_stmt = con.insert().values(
                        character_id=new_char_id,
                        counter=con_row[2],
                        title=con_row[3],
                        number=con_row[4],
                        auto_increment=con_row[5],
                        time=con_row[6],
                        visible=con_row[7],
                    )
                    await conn.execute(add_con_stmt)

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
    metadata = db.MetaData()
    try:
        # load tables
        emp = await get_tracker_table(ctx, metadata, engine)
        con = await get_condition_table(ctx, metadata, engine)
        macro = await get_macro_table(ctx, metadata, engine)

        # find the character
        stmt = emp.select().where(emp.c.name == character)

        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(stmt):
                # print(row)
                data.append(row)
            # print(data)
            primary_id = data[0][0]

            # Manual Cascade Drop
            try:
                con_del_stmt = delete(con).where(con.c.character_id == primary_id)
                await conn.execute(con_del_stmt)
            except Exception as e:
                pass
            try:
                macro_del_stmt = delete(macro).where(macro.c.character_id == primary_id)
                await conn.execute(macro_del_stmt)
            except Exception as e:
                pass

            stmt = delete(emp).where(emp.c.id == primary_id)
            await conn.execute(stmt)

        # Fix initiative position after delete:
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


def calculate_hp(chp, maxhp):
    hp_string = ''
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
    metadata = db.MetaData()
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = emp.select().where(emp.c.name == name)
        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(stmt):
                data.append(row)

            thp = data[0][7]
            new_thp = thp + amount

            stmt = update(emp).where(emp.c.name == name).values(
                temp_hp=new_thp
            )

            result = await conn.execute(stmt)
            if result.rowcount == 0:
                return False
        await engine.dispose()
        return True

    except Exception as e:
        print(f'add_thp: {e}')
        report = ErrorReport(ctx, add_thp.__name__, e, bot)
        await report.report()
        return False


async def change_hp(ctx: discord.ApplicationContext, engine, bot, name: str, amount: int, heal: bool):
    metadata = db.MetaData()
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = emp.select().where(emp.c.name == name)
        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(stmt):
                data.append(row)

            chp = data[0][5]
            new_hp = chp
            maxhp = data[0][6]
            thp = data[0][7]
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

            stmt = update(emp).where(emp.c.name == name).values(
                current_hp=new_hp,
                temp_hp=new_thp
            )

            result = await conn.execute(stmt)
            if result.rowcount == 0:
                return False
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
    metadata = db.MetaData()
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = update(emp).where(emp.c.name == name).values(
            init=init
        )
        async with engine.begin() as conn:
            result = await conn.execute(stmt)
            # conn.commit()
            if result.rowcount == 0:
                return False
        return True
    except Exception as e:
        print(f'set_init: {e}')
        report = ErrorReport(ctx, set_init.__name__, e, bot)
        await report.report()
        return False


# Check to make sure that the character is in the right place in initiative
async def init_integrity_check(ctx: discord.ApplicationContext, init_pos: int, current_character: str, engine):
    init_list = await get_init_list(ctx, engine)
    if init_list[init_pos][1] == current_character:
        return True
    else:
        return False


# Upgraded Advance Initiative Function to work with block initiative options
async def block_advance_initiative(ctx: discord.ApplicationContext, engine, bot):
    metadata = db.MetaData()
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
            emp = await get_tracker_table(ctx, metadata, engine)
            con = await get_condition_table(ctx, metadata, engine)

            # print(f"guild.initiative: {guild.initiative}")
            if guild.initiative is None:
                init_pos = -1
                guild.round = 1
                first_pass = True

                # set init
                stmt = emp.select()
                dice = DiceRoller('')
                async with engine.begin() as conn:
                    for row in await conn.execute(stmt):
                        if row[2] == 0:
                            roll = await dice.plain_roll(row[8])
                            # print(f"Name: {row[1]}, roll: {roll}")
                            await set_init(ctx, bot, row[1], roll[1], engine)
            else:
                init_pos = int(guild.initiative)

            init_list = await get_init_list(ctx, engine)

            if guild.saved_order == '':
                current_character = init_list[0][1]
            else:
                current_character = guild.saved_order

            # Record the initial to break an infinite loop
            iterations = 0

            while not block_done:
                # print(f"init_pos: {init_pos}")

                # make sure that the current character is at the same place in initiative as it was before
                # decrement any conditions with the decrement flag

                if guild.block:  # if in block initiative, decrement conditions at the beginning of the turn
                    # if its not, set the init position to the position of the current character before advancing it
                    # print("Yes guild.block")
                    if not await init_integrity_check(ctx, init_pos, current_character, engine) and not first_pass:
                        # print(f"integrity check was false: init_pos: {init_pos}")
                        for pos, row in enumerate(init_list):
                            if row[1] == current_character:
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

                try:
                    stmt = emp.select().where(emp.c.name == current_character)
                    async with engine.begin() as conn:
                        data = []
                        for row in await conn.execute(stmt):
                            data.append(row)
                            # print(row)
                except Exception as e:
                    print(f'advance_initiative: {e}')
                    report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
                    await report.report()
                    return False

                try:
                    stmt = con.select().where(con.c.character_id == data[0][0])
                    async with engine.begin() as conn:
                        for con_row in await conn.execute(stmt):
                            if con_row[5] and not con_row[6]:  # If auto-increment and NOT time
                                if con_row[4] >= 2:  # if number >= 2
                                    new_stmt = update(con).where(con.c.id == con_row[0]).values(
                                        number=con_row[4] - 1
                                    )  # number --
                                else:
                                    new_stmt = delete(con).where(
                                        con.c.id == con_row[0])  # If number is 1 or 0, delete it
                                    await ctx.channel.send(f"{con_row[3]} removed from {data[0][1]}")
                                await conn.execute(new_stmt)
                            elif con_row[6]:  # If time is true
                                time_stamp = datetime.datetime.fromtimestamp(con_row[4])  # The number is a timestamp
                                # for the expiration, not a round count
                                current_time = await get_time(ctx, engine, bot)
                                time_left = time_stamp - current_time
                                if time_left.total_seconds() <= 0:
                                    new_stmt = delete(con).where(
                                        con.c.id == con_row[0])  # If the time left is 0 or left, delete it
                                    await ctx.channel.send(f"{con_row[3]} removed from {data[0][1]}")
                                    await conn.execute(new_stmt)
                except Exception as e:
                    print(f'block_advance_initiative: {e}')
                    report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
                    await report.report()

                if not guild.block:  # if not in block initiative, decrement the conditions at the end of the turn
                    # print("Not guild.block")
                    # if its not, set the init position to the position of the current character before advancing it
                    if not await init_integrity_check(ctx, init_pos, current_character, engine) and not first_pass:
                        # print(f"integrity check was false: init_pos: {init_pos}")
                        for pos, row in enumerate(init_list):
                            if row[1] == current_character:
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

                # block initiative loop
                # check to see if the next character is player vs npc
                # print(init_list)
                # print(f"init_pos: {init_pos}, len(init_list): {len(init_list)}")
                if init_pos >= len(init_list) - 1:
                    # print(f"init_pos: {init_pos}")
                    if init_list[init_pos][3] != init_list[0][3]:
                        block_done = True
                elif init_list[init_pos][3] != init_list[init_pos + 1][3]:
                    block_done = True
                if not guild.block:
                    block_done = True

                turn_list.append(init_list[init_pos][1])
                current_character = init_list[init_pos][1]
                iterations += 1
                if iterations >= len(init_list):  # stop an infinite loop
                    block_done = True

                # print(turn_list)

            # Out side while statement - for reference
            guild.initiative = init_pos  # set it
            # print(f"final init_pos: {init_pos}")
            guild.saved_order = str(init_list[init_pos][1])
            await session.commit()
        await engine.dispose()
        return True
    except Exception as e:
        print(f"block_advance_initiative: {e}")
        report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
        await report.report()


async def get_init_list(ctx: discord.ApplicationContext, engine):
    try:
        metadata = db.MetaData()
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = emp.select().order_by(emp.c.init.desc()).order_by(emp.c.id.desc())
        # print(stmt)
        data = []
        async with engine.begin() as conn:
            for row in await conn.execute(stmt):
                # print(row)
                data.append(row)
            # print(data)
        await engine.dispose()
        return data

    except Exception as e:
        print("error in get_init_list")
        return []


def parse_init_list(init_list: list):
    parsed_list = []
    for row in init_list:
        parsed_list.append(row[1])
    return parsed_list


def ping_player_on_init(init_list: list, selected: int):
    selected_char = init_list[selected]
    user = selected_char[4]
    return f"<@{user}>, it's your turn."


# Builds the tracker string. Updated to work with block initiative
async def block_get_tracker(init_list: list, selected: int, ctx: discord.ApplicationContext, engine, bot,
                            gm: bool = False):
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
        if guild.block and guild.initiative != None:
            turn_list = await get_turn_list(ctx, engine, bot)
            block = True
        else:
            block = False
        round = guild.round
    try:
        if await check_timekeeper(ctx, engine):
            datetime_string = f" {await output_datetime(ctx, engine, bot)}\n" \
                              f"________________________\n"
    except NoResultFound as e:
        await ctx.channel.send(
            error_not_initialized,
            delete_after=30)
    except Exception as e:
        print(f'get_tracker: {e}')
        report = ErrorReport(ctx, "get_tracker", e, bot)
        await report.report()

    try:
        metadata = db.MetaData()
        con = await get_condition_table(ctx, metadata, engine)
        row_data = []
        for row in init_list:
            stmt = con.select().where(con.c.character_id == row[0])
            compiled = stmt.compile()
            # print(compiled)
            async with engine.connect() as conn:
                con_data = []
                # print(conn.execute)
                for con_row in await conn.execute(stmt):
                    con_data.append(con_row)
                    # print(con_row)
                await conn.close()

            row_data.append({'id': row[0],
                             'name': row[1],
                             'init': row[2],
                             'player': row[3],
                             'user': row[4],
                             'chp': row[5],
                             'maxhp': row[6],
                             'thp': row[7],
                             'cc': con_data
                             })

        if round != 0:
            round_string = f"Round: {round}"
        else:
            round_string = ""

        output_string = f"```{datetime_string}" \
                        f"Initiative: {round_string}\n"
        for x, row in enumerate(row_data):
            sel_bool = False
            selector = ''

            # don't show an init if not in combat
            if row['init'] == 0:
                init_string = ""
            else:
                init_string = f"{row['init']}"

            if block:
                for character in turn_list:
                    if row['id'] == character[0]:
                        sel_bool = True
            else:
                if x == selected:
                    sel_bool = True

            # print(f"{row['name']}: x: {x}, selected: {selected}")

            if sel_bool:
                selector = '>>'
            if row['player'] or gm:
                if row['thp'] != 0:
                    string = f"{selector} {init_string} {str(row['name']).title()}: {row['chp']}/{row['maxhp']} ({row['thp']}) Temp\n"
                else:
                    string = f"{selector}  {init_string} {str(row['name']).title()}: {row['chp']}/{row['maxhp']}\n"
            else:
                hp_string = calculate_hp(row['chp'], row['maxhp'])
                string = f"{selector}  {init_string} {str(row['name']).title()}: {hp_string} \n"
            output_string += string

            # TODO Adjust how the tracker displays the PF2 /a stats, as its going to get crowded fast
            for con_row in row['cc']:
                if con_row[7] == True:
                    if gm or not con_row[2]:
                        if con_row[4] != None:
                            if con_row[6]:
                                time_stamp = datetime.datetime.fromtimestamp(con_row[4])
                                current_time = await get_time(ctx, engine, bot)
                                time_left = time_stamp - current_time
                                days_left = time_left.days
                                processed_minutes_left = divmod(time_left.seconds, 60)[0]
                                processed_seconds_left = divmod(time_left.seconds, 60)[1]
                                if days_left != 0:
                                    con_string = f"       {con_row[3]}: {days_left} Days, {processed_minutes_left}:{processed_seconds_left}\n"
                                else:
                                    con_string = f"       {con_row[3]}: {processed_minutes_left}:{processed_seconds_left}\n"
                            else:
                                con_string = f"       {con_row[3]}: {con_row[4]}\n"
                        else:
                            con_string = f"       {con_row[3]}\n"

                    elif con_row[2] == True and sel_bool and row['player']:
                        con_string = f"       {con_row[3]}: {con_row[4]}\n"
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
        print(f"block_get_tracker: {e}")
        report = ErrorReport(ctx, block_get_tracker.__name__, e, bot)
        await report.report()


# Gets the locations of the pinned trackers, then updates them with the newest tracker
async def update_pinned_tracker(ctx: discord.ApplicationContext, engine, bot):
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

            # Update the GM tracker
            if gm_tracker is not None:
                gm_tracker_display_string = await block_get_tracker(await get_init_list(ctx, engine), guild.initiative,
                                                                    ctx,
                                                                    engine,
                                                                    bot,
                                                                    gm=True)
                gm_channel = bot.get_channel(gm_tracker_channel)
                gm_message = await gm_channel.fetch_message(gm_tracker)
                await gm_message.edit(gm_tracker_display_string)
        except NoResultFound as e:
            await ctx.channel.send(
                error_not_initialized,
                delete_after=30)
        except Exception as e:
            print(f'update_pinned_tracker: {e}')
            report = ErrorReport(ctx, update_pinned_tracker.__name__, e, bot)
            await report.report()


async def block_post_init(ctx: discord.ApplicationContext, engine, bot: discord.Bot):
    # Query the initiative position for the tracker and post it
    # try:
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
        if guild.block:
            turn_list = await get_turn_list(ctx, engine, bot)
            block = True
            # print(f"block_post_init: \n {turn_list}")
        else:
            block = False

        init_list = await get_init_list(ctx, engine)
        tracker_string = await block_get_tracker(init_list, guild.initiative, ctx, engine, bot)
        try:
            ping_string = ''
            if block:
                for character in turn_list:
                    user = bot.get_user(character[4])
                    ping_string += f"{user.mention}, it's your turn.\n"
            else:
                user = bot.get_user(init_list[guild.initiative][4])
                ping_string += f"{user.mention}, it's your turn.\n"
        except Exception as e:
            # print(f'post_init: {e}')
            ping_string = ''

        # Always post the tracker to the player channel
        if ctx.channel.id == guild.tracker_channel:
            await ctx.send_followup(f"{tracker_string}\n"
                                    f"{ping_string}")
        else:
            await bot.get_channel(guild.tracker_channel).send(f"{tracker_string}\n"
                                                              f"{ping_string}")
            await ctx.send_followup("Initiative Advanced.")
    await engine.dispose()
    # except NoResultFound as e:
    #     await ctx.channel.send(error_not_initialized,
    #                            delete_after=30)
    # except Exception as e:
    #     print(f"block_post_init: {e}")
    #     report = ErrorReport(ctx, block_post_init.__name__, e, bot)
    #     await report.report()


# Note: Works backwards
async def get_turn_list(ctx: discord.ApplicationContext, engine, bot):
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
            iteration = 0
            init_pos = guild.initiative
            init_list = await get_init_list(ctx, engine)
            length = len(init_list)
            while not block_done:
                turn_list.append(init_list[init_pos])
                # print(f"init_pos: {init_pos}, turn_list: {turn_list}")
                player_status = init_list[init_pos][3]
                if init_pos == 0:
                    if player_status != init_list[length - 1][3]:
                        block_done = True
                else:
                    if player_status != init_list[init_pos - 1][3]:
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
                 unit: str, auto_decrement: bool, bot):
    metadata = db.MetaData()
    # Get the Character's data

    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = emp.select().where(emp.c.name == character)

        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(stmt):
                data.append(row)
                # print(row)
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

            con = await get_condition_table(ctx, metadata, engine)

            if not guild.timekeeping or unit == 'Round':

                stmt = con.insert().values(
                    character_id=data[0][0],
                    title=title,
                    number=number,
                    counter=counter,
                    auto_increment=auto_decrement,
                    time=False
                )
                async with engine.begin() as conn:
                    await conn.execute(stmt)
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

                stmt = con.insert().values(
                    character_id=data[0][0],
                    title=title,
                    number=timestamp,
                    counter=counter,
                    auto_increment=True,
                    time=True
                )
                async with engine.begin() as conn:
                    await conn.execute(stmt)
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
    metadata = db.MetaData()
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = emp.select().where(emp.c.name == character)

        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(stmt):
                data.append(row)
                # print(row)
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
        con = await get_condition_table(ctx, metadata, engine)
        check_stmt = con.select().where(con.c.character_id == data[0][0]).where(con.c.title == condition)
        async with engine.begin() as conn:
            check_data = []
            for row in await conn.execute(check_stmt):
                if row[6]:
                    await ctx.send_followup("Unable to edit time based conditions. Try again in a future update.",
                                            ephemeral=True)
                    return False
                else:
                    stmt = update(con).where(con.c.character_id == data[0][0]).where(con.c.title == condition).values(
                        number=value
                    )
                    await conn.execute(stmt)
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
    metadata = db.MetaData()
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = emp.select().where(emp.c.name == character)
        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(stmt):
                data.append(row)
                # print(row)
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
        con = await get_condition_table(ctx, metadata, engine)
        stmt = delete(con).where(con.c.character_id == data[0][0]).where(con.c.title == condition).where(
            con.c.visible == True)
        async with engine.begin() as conn:
            await conn.execute(stmt)
            # print(result)
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
    metadata = db.MetaData()
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = emp.select().where(emp.c.name == character)
        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(stmt):
                data.append(row)
                # print(row)
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'get_cc: {e}')
        report = ErrorReport(ctx, get_cc.__name__, e, bot)
        await report.report()

    try:
        con = await get_condition_table(ctx, metadata, engine)
        stmt = con.select().where(con.c.character_id == data[0][0]).where(con.c.counter == True)

        con_data = []
        async with engine.begin() as conn:
            result = await conn.execute(stmt)
            for row in result:
                con_data.append(row)
        await engine.dispose()
        return con_data
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
    metadata = db.MetaData()
    current_time = await get_time(ctx, engine, bot)
    con = await get_condition_table(ctx, metadata, engine)
    emp = await get_tracker_table(ctx, metadata, engine)
    stmt = con.select().where(con.c.time == True)
    async with engine.begin() as conn:
        for row in await conn.execute(stmt):
            time_stamp = datetime.datetime.fromtimestamp(row[4])
            time_left = time_stamp - current_time
            if time_left.total_seconds() <= 0:
                char_stmt = emp.select().where(emp.c.id == row[1])
                char_name = ''
                for char_row in await conn.execute(char_stmt):
                    char_name = char_row[1]
                del_stmt = delete(con).where(con.c.id == row[0])
                await ctx.channel.send(f"{row[3]} removed from {char_name}")
                await conn.execute(del_stmt)
    await engine.dispose()


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# UTILITY FUNCTIONS

# Checks to see if the user of the slash command is the GM, returns a boolean
async def gm_check(ctx, engine):
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
    metadata = db.MetaData()
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        stmt = select(emp.c.player).where(emp.c.name == character)
        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(stmt):
                data.append(row)
        return data[0]
    except Exception as e:
        print(f'player_check: {e}')
        report = ErrorReport(ctx, player_check.__name__, e, bot)
        await report.report()


#############################################################################
#############################################################################
# Specific character modals

class PF2AddCharacterModal(discord.ui.Modal):
    def __init__(self, name: str, hp: int, init: str, initiative, player, ctx, emp, con, engine, bot, *args, **kwargs):
        self.name = name
        self.hp = hp
        self.init = init
        self.initiative = initiative
        self.player = player
        self.ctx = ctx
        self.emp = emp
        self.con = con
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

        emp_stmt = self.emp.insert().values(
            name=self.name,
            init_string=self.init,
            init=self.initiative,
            player=self.player,
            user=self.ctx.user.id,
            current_hp=self.hp,
            max_hp=self.hp,
            temp_hp=0
        )
        async with self.engine.begin() as conn:
            result = await conn.execute(emp_stmt)
            id_stmt = self.emp.select().where(self.emp.c.name == self.name)
            id_data = []
            for row in await conn.execute(id_stmt):
                id_data.append(row)

            char_dicts = [{
                'character_id': id_data[0][0],
                'title': 'AC',
                'number': int(self.children[0].value),
                'counter': True,
                'visible': False
            },
                {
                    'character_id': id_data[0][0],
                    'title': 'Fort',
                    'number': int(self.children[1].value),
                    'counter': True,
                    'visible': False
                },
                {
                    'character_id': id_data[0][0],
                    'title': 'Reflex',
                    'number': int(self.children[2].value),
                    'counter': True,
                    'visible': False
                },
                {
                    'character_id': id_data[0][0],
                    'title': 'Will',
                    'number': int(self.children[3].value),
                    'counter': True,
                    'visible': False
                },
                {
                    'character_id': id_data[0][0],
                    'title': 'DC',
                    'number': int(self.children[4].value),
                    'counter': True,
                    'visible': False
                },
            ]

            con_stmt = self.con.insert().values(
                char_dicts
            )
            await conn.execute(con_stmt)
        await update_pinned_tracker(self.ctx, self.engine, self.bot)

        await interaction.response.send_message(embeds=[embed])


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
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

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
        metadata = db.MetaData()
        character_list = []

        try:
            emp = await get_tracker_table(ctx, metadata, self.engine)
            stmt = emp.select()
            async  with self.engine.begin() as conn:
                data = []
                for row in await conn.execute(stmt):
                    data.append(row)
                    # print(row)
            for row in data:
                # if row[4] == ctx.interaction.user.id or gm_status:
                character_list.append(row[1])
            # print(character_list)
            await self.engine.dispose()
            return character_list
        except Exception as e:
            print(f'character_select: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return False

    # Autocomplete to return the list of character the user owns, or all if the user is the GM
    async def character_select_gm(self, ctx: discord.AutocompleteContext):
        metadata = db.MetaData()
        character_list = []

        gm_status = await gm_check(ctx, self.engine)

        try:
            emp = await get_tracker_table(ctx, metadata, self.engine)
            stmt = emp.select()
            async with self.engine.begin() as conn:
                data = []
                for row in await conn.execute(stmt):
                    data.append(row)
                    # print(row)
            for row in data:
                if row[4] == ctx.interaction.user.id or gm_status:
                    character_list.append(row[1])
            # print(character_list)
            await self.engine.dispose()
            return character_list

        except Exception as e:
            print(f'character_select_gm: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return False

    async def cc_select(self, ctx: discord.AutocompleteContext):
        metadata = db.MetaData()
        character = ctx.options['character']
        con = await get_condition_table(ctx, metadata, self.engine)
        emp = await get_tracker_table(ctx, metadata, self.engine)

        char_stmt = emp.select().where(emp.c.name == character)
        # print(character)
        async with self.engine.begin() as conn:
            data = []
            con_list = []
            for char_row in await conn.execute(char_stmt):
                data.append(char_row)
            for row in data:
                # print(row)
                con_stmt = con.select().where(con.c.character_id == row[0])
                for char_row in await conn.execute(con_stmt):
                    # print(char_row)
                    con_list.append(f"{char_row[3]}")
        await self.engine.dispose()
        return con_list

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

    @char.command(description="Add PC on NPC",
                  # guild_ids=[GUILD]
                  )
    @option('name', description="Character Name", input_type=str)
    @option('hp', description='Total HP', input_type=int)
    @option('player', choices=['player', 'npc'], input_type=str)
    @option('initiative', description="Initiative Roll (XdY+Z)", required=True, input_type=str)
    async def add(self, ctx: discord.ApplicationContext, name: str, hp: int,
                  player: str, initiative: str):
        # await ctx.response.defer()
        response = False
        player_bool = False
        if player == 'player':
            player_bool = True
        elif player == 'npc':
            player_bool = False

        response = await add_character(ctx, self.engine, self.bot, name, hp, player_bool, initiative)
        if not response:
            await ctx.send_followup(f"Error Adding Character", ephemeral=True)

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

    @char.command(description="Duplicate NPC")
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

    @i.command(description="Manage Initiative",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    @option('mode', choices=['start', 'stop', 'delete character'], required=True)
    @option('character', description='Character to delete', required=False)
    async def manage(self, ctx: discord.ApplicationContext, mode: str, character: str = ''):
        # try:
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
                    guild.initiative = None
                    guild.saved_order = ''
                    guild.round = 0
                    metadata = db.MetaData()
                    # Update the tables
                    emp = await get_tracker_table(ctx, metadata, self.engine)
                    init_stmt = emp.select()
                    # tracker cleanup

                    con = await get_condition_table(ctx, metadata, self.engine)
                    stmt = delete(con).where(con.c.counter == False).where(con.c.auto_increment == True).where(
                        con.c.time == False)
                    clean_stmt = emp.select().where(emp.c.current_hp <= 0).where(
                        emp.c.player == False)  # select all npcs with 0 HP

                    async with self.engine.begin() as conn:
                        await conn.execute(stmt)  # delete any auto-decrementing round based conditions
                        for row in await conn.execute(
                                init_stmt):  # Set the initiatives of all characters to 0 (out of combat)
                            stmt = update(emp).where(emp.c.name == row[1]).values(
                                init=0
                            )
                            await conn.execute(stmt)

                        for row in await conn.execute(clean_stmt):
                            await delete_character(ctx, row[1], self.engine, self.bot)

                        # print(result)
                    await update_pinned_tracker(ctx, self.engine, self.bot)
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
        # except NoResultFound as e:
        #     await ctx.respond(
        #         error_not_initialized,
        #         ephemeral=True)
        #     return False
        # except IndexError as e:
        #     await ctx.respond("Ensure that you have added characters to the initiative list.")
        # except Exception as e:
        #     await ctx.respond("Failed")

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
    async def add(self, ctx: discord.ApplicationContext, character: str, title: str, type: str, number: int = None,
                  unit: str = "Round",
                  auto: str = 'Static'):
        await ctx.response.defer(ephemeral=True)
        if type == "Condition":
            counter_bool = False
        else:
            counter_bool = True
        if auto == 'Auto Decrement':
            auto_bool = True
        else:
            auto_bool = False

        response = await set_cc(ctx, self.engine, character, title, counter_bool, number, unit, auto_bool, self.bot)
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
                    counter_string = f'{row[3]}: {row[4]}'
                    output_string += counter_string
                    output_string += '\n'
                output_string += "```"
                await ctx.send_followup(output_string, ephemeral=True)
        except Exception as e:
            print(f'cc_show: {e}')
            await ctx.send_followup(f'Failed: Ensure that {character} is a valid character', ephemeral=True)


def setup(bot):
    bot.add_cog(InitiativeCog(bot))
