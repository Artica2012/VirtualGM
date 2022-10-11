# initiative.py
# Initiative Tracker Module
import datetime
import os

# imports
import discord
import asyncio
import sqlalchemy as db
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from database_models import Global, Base, TrackerTable, ConditionTable
from database_operations import get_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport
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

# Set up the tracker if it does not exit.db
async def setup_tracker(ctx: discord.ApplicationContext, engine, bot, gm: discord.User, channel: discord.TextChannel,
                        gm_channel: discord.TextChannel):
    # Check to make sure bot has permissions in both channels
    if not channel.can_send() or gm_channel.can_send():
        await ctx.respond("Setup Failed. Ensure VirtualGM has message posting permissions in both channels.",
                          ephemeral=True)
        return False

    try:
        conn = engine.connect()
        metadata = db.MetaData()

        Base.metadata.create_all(engine)

        with Session(engine) as session:
            guild = Global(
                guild_id=ctx.guild_id,
                time=0,
                gm=gm.id,
                tracker_channel=channel.id,
                gm_tracker_channel=gm_channel.id
            )
            session.add(guild)
            session.commit()
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        con = ConditionTable(ctx, metadata, engine).condition_table()
        metadata.create_all(engine)

        await set_pinned_tracker(ctx, engine, bot, channel)  # set the tracker in the player channel
        await set_pinned_tracker(ctx, engine, bot, gm_channel, gm=True)  # set up the gm_track in the GM channel
        return True


    except Exception as e:
        print(f'setup_tracker: {e}')
        report = ErrorReport(ctx, setup_tracker.__name__, e, bot)
        await report.report()
        await ctx.respond("Server Setup Failed. Perhaps it has already been set up?", ephemeral=True)
        return False


async def set_gm(ctx: discord.ApplicationContext, new_gm: discord.User, engine, bot):
    try:
        conn = engine.connect()
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            guild.gm = new_gm.id
            session.commit()

        return True
    except Exception as e:
        print(f'set_gm: {e}')
        report = ErrorReport(ctx, set_gm.__name__, e, bot)
        await report.report()
        return False


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# CHARACTER MANAGEMENT

# Add a character to the database
async def add_character(ctx: discord.ApplicationContext, engine, bot, name: str, hp: int,
                        player_bool: bool, init: str):
    metadata = db.MetaData()
    dice = DiceRoller('')
    insp = db.inspect(engine)

    try:
        # print(f"Init: {init}")
        initiative = int(init)
    except:
        try:
            roll = dice.plain_roll(init)
            initiative = roll[1]
            if type(initiative) != int:
                return False
        except:
            return False

    try:
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        with Session(engine) as session:
            guild = session.scalars(select(Global))
            for row in guild:
                if not insp.has_table(emp.name):
                    metadata.create_all(engine)

        stmt = emp.insert().values(
            name=name,
            init=initiative,
            player=player_bool,
            user=ctx.user.id,
            current_hp=hp,
            max_hp=hp,
            temp_hp=0
        )
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # conn.commit()
            await ctx.respond(f"Character {name} added successfully with initiative {initiative}", ephemeral=True)
        return True
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
                               delete_after=30)
        return False
    except Exception as e:
        print(f'add_character: {e}')
        report = ErrorReport(ctx, add_character.__name__, e, bot)
        await report.report()
        return False


async def delete_character(ctx: discord.ApplicationContext, character: str, engine, bot):
    metadata = db.MetaData()
    try:
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        con = ConditionTable(ctx, metadata, engine).condition_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                # print(row)
                data.append(row)
            # print(data)
            primary_id = data[0][0]
            con_del_stmt = delete(con).where(con.c.character_id == primary_id)
            conn.execute(con_del_stmt)
            stmt = delete(emp).where(emp.c.id == primary_id)
            conn.execute(stmt)

        # Fix initiative position after delete:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            if guild.initiative is None:
                return True
            elif guild.saved_order == '':
                return True
            else:
                init_pos = int(guild.initiative)
                current_character = guild.saved_order
                if not init_integrity_check(ctx, init_pos, current_character, engine):
                    for pos, row in enumerate(get_init_list(ctx, engine)):
                        if row[1] == current_character:
                            init_pos = pos
                guild.initiative = init_pos
                session.commit()

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
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = emp.select().where(emp.c.name == name)
        compiled = stmt.compile()
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)

        thp = data[0][7]
        new_thp = thp + amount

        stmt = update(emp).where(emp.c.name == name).values(
            temp_hp=new_thp
        )
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # conn.commit()
            if result.rowcount == 0:
                return False
        return True

    except Exception as e:
        print(f'add_thp: {e}')
        report = ErrorReport(ctx, add_thp.__name__, e, bot)
        await report.report()
        return False


async def change_hp(ctx: discord.ApplicationContext, engine, bot, name: str, amount: int, heal: bool):
    metadata = db.MetaData()
    try:
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = emp.select().where(emp.c.name == name)
        compiled = stmt.compile()
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
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
                await ctx.channel.send(f'```HP: {new_hp}```')

            stmt = update(emp).where(emp.c.name == name).values(
                current_hp=new_hp,
                temp_hp=new_thp
            )
            compiled = stmt.compile()
            with engine.connect() as conn:
                result = conn.execute(stmt)
                # conn.commit()
                if result.rowcount == 0:
                    return False
            return True
    except Exception as e:
        print(f'change_hp: {e}')
        report = ErrorReport(ctx, change_hp.__name__, e, bot)
        await report.report()
        return False
    try:
        stmt = update(emp).where(emp.c.name == name).values(
            current_hp=new_hp,
            temp_hp=new_thp
        )
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # conn.commit()
            if result.rowcount == 0:
                return False
        return True
    except Exception as e:
        print(f'change_hp: {e}')
        return False


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# TRACKER MANAGEMENT

async def repost_trackers(ctx: discord.ApplicationContext, engine, bot):
    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            channel = bot.get_channel(guild.tracker_channel)
            gm_channel = bot.get_channel(guild.gm_tracker_channel)
            await set_pinned_tracker(ctx, engine, bot, channel)  # set the tracker in the player channel
            await set_pinned_tracker(ctx, engine, bot, gm_channel, gm=True)  # set up the gm_track in the GM channel
            return True
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
                               delete_after=30)
        return False
    except Exception as e:
        print(f'repost_trackers: {e}')
        report = ErrorReport(ctx, repost_trackers.__name__, e, bot)
        await report.report()
        return False


async def set_pinned_tracker(ctx: discord.ApplicationContext, engine, bot, channel: discord.TextChannel, gm=False):
    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()

            try:
                init_pos = int(guild.initiative)
            except Exception as e:
                init_pos = None
            display_string = await block_get_tracker(get_init_list(ctx, engine), init_pos, ctx, engine,
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
            session.commit()
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
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = update(emp).where(emp.c.name == name).values(
            init=init
        )
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # conn.commit()
            if result.rowcount == 0:
                # print("RowCount = 0")
                return False
        return True
    except Exception as e:
        print(f'set_init: {e}')
        report = ErrorReport(ctx, set_init.__name__, e, bot)
        await report.report()
        return False


# Check to make sure that the character is in the right place in initiative
def init_integrity_check(ctx: discord.ApplicationContext, init_pos: int, current_character: str, engine):
    init_list = get_init_list(ctx, engine)
    if init_list[init_pos][1] == current_character:
        return True
    else:
        return False


# Upgraded Advance Initiative Function to work with block initiative options
async def block_advance_initiative(ctx: discord.ApplicationContext, engine, bot):
    metadata = db.MetaData()
    block_done = False
    turn_list = []

    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            emp = TrackerTable(ctx, metadata, engine).tracker_table()
            con = ConditionTable(ctx, metadata, engine).condition_table()
            init_list = get_init_list(ctx, engine)
            if guild.initiative is None:
                init_pos = -1
                guild.round = 0
            else:
                init_pos = int(guild.initiative)
            if guild.saved_order == '':
                current_character = init_list[0][1]
            else:
                current_character = guild.saved_order

            while not block_done:

                # make sure that the current character is at the same place in initiative as it was before
                # decrement any conditions with the decrement flag
                try:
                    stmt = emp.select().where(emp.c.name == current_character)
                    compiled = stmt.compile()
                    # print(compiled)
                    with engine.connect() as conn:
                        data = []
                        for row in conn.execute(stmt):
                            data.append(row)
                            # print(row)
                except Exception as e:
                    print(f'advance_initiative: {e}')
                    report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
                    await report.report()
                    return False

                try:
                    stmt = con.select().where(con.c.character_id == data[0][0])
                    compiled = stmt.compile()
                    with engine.connect() as conn:
                        for con_row in conn.execute(stmt):
                            if con_row[5] and not con_row[6]:
                                if con_row[4] >= 2:
                                    new_stmt = update(con).where(con.c.id == con_row[0]).values(
                                        number=con_row[4] - 1
                                    )
                                else:
                                    new_stmt = delete(con).where(con.c.id == con_row[0])
                                    await ctx.channel.send(f"{con_row[3]} removed from {data[0][1]}")
                                result = conn.execute(new_stmt)
                            elif con_row[6]:
                                time_stamp = datetime.datetime.fromtimestamp(con_row[4])
                                current_time = await get_time(ctx, engine, bot)
                                time_left = time_stamp - current_time
                                if time_left.total_seconds() <= 0:
                                    new_stmt = delete(con).where(con.c.id == con_row[0])
                                    await ctx.channel.send(f"{con_row[3]} removed from {data[0][1]}")
                                    result = conn.execute(new_stmt)
                except Exception as e:
                    print(f'block_advance_initiative: {e}')
                    report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
                    await report.report()

                # if its not, set the init position to the position of the current character before advancing it
                if not init_integrity_check(ctx, init_pos, current_character, engine):
                    for pos, row in enumerate(init_list):
                        if row[1] == current_character:
                            init_pos = pos

                init_pos += 1  # increase the init position by 1
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
                # print(turn_list)

            # Out side while statement - for reference
            guild.initiative = init_pos  # set it
            guild.saved_order = str(init_list[init_pos][1])
            session.commit()
            return True
    except Exception as e:
        print(f"block_advance_initiative: {e}")
        report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
        await report.report()


def get_init_list(ctx: discord.ApplicationContext, engine):
    try:
        metadata = db.MetaData()
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = emp.select().order_by(emp.c.init.desc())
        # print(stmt)
        data = []
        with engine.connect() as conn:
            for row in conn.execute(stmt):
                # print(row)
                data.append(row)
            # print(data)
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
    with Session(engine) as session:
        guild = session.execute(select(Global).filter(
            or_(
                Global.tracker_channel == ctx.channel.id,
                Global.gm_tracker_channel == ctx.channel.id
            )
        )
        ).scalar_one()
        if guild.block and guild.initiative != None:
            turn_list = await get_turn_list(ctx, engine, bot)
            block = True
        else:
            block = False
    try:
        if check_timekeeper(ctx, engine):
            datetime_string = f" {await output_datetime(ctx, engine, bot)}\n" \
                              f"________________________\n"
    except NoResultFound as e:
        await ctx.channel.send(
            "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
            "proper channel or run `/i admin setup` to setup the initiative tracker",
            delete_after=30)
    except Exception as e:
        print(f'get_tracker: {e}')
        report = ErrorReport(ctx, "get_tracker", e, bot)
        await report.report()

    try:
        metadata = db.MetaData()
        con = ConditionTable(ctx, metadata, engine).condition_table()
        row_data = []
        for row in init_list:
            stmt = con.select().where(con.c.character_id == row[0])
            compiled = stmt.compile()
            # print(compiled)
            with engine.connect() as conn:
                con_data = []
                # print(conn.execute)
                for con_row in conn.execute(stmt):
                    con_data.append(con_row)
                    # print(con_row)

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

        output_string = f"```{datetime_string}" \
                        f"Initiative:\n"
        for x, row in enumerate(row_data):
            selector = ''
            if block:
                for character in turn_list:
                    if row['id'] == character[0]:
                        selector = '>>'
            else:
                if x == selected:
                    selector = '>>'
            if row['player'] or gm:
                if row['thp'] != 0:
                    string = f"{selector} {row['init']} {str(row['name']).title()}: {row['chp']}/{row['maxhp']} ({row['thp']}) Temp\n"
                else:
                    string = f"{selector}  {row['init']} {str(row['name']).title()}: {row['chp']}/{row['maxhp']}\n"
            else:
                hp_string = calculate_hp(row['chp'], row['maxhp'])
                string = f"{selector}  {row['init']} {str(row['name']).title()}: {hp_string} \n"
            output_string += string

            for con_row in row['cc']:
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

                elif con_row[2] == True and x == selected and row['player']:
                    con_string = f"       {con_row[3]}: {con_row[4]}\n"
                else:
                    con_string = ''
                output_string += con_string
        output_string += f"```"
        # print(output_string)
        return output_string
    except Exception as e:
        print(f"block_get_tracker: {e}")
        report = ErrorReport(ctx, block_get_tracker.__name__, e, bot)
        await report.report()


async def update_pinned_tracker(ctx: discord.ApplicationContext, engine, bot):
    with Session(engine) as session:
        try:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()

            tracker = guild.tracker
            tracker_channel = guild.tracker_channel
            gm_tracker = guild.gm_tracker
            gm_tracker_channel = guild.gm_tracker_channel

            # Update the tracker
            if tracker is not None:
                tracker_display_string = await block_get_tracker(get_init_list(ctx, engine), guild.initiative, ctx, engine,
                                                                 bot)
                channel = bot.get_channel(tracker_channel)
                message = await channel.fetch_message(tracker)
                await message.edit(tracker_display_string)

            # Update the GM tracker
            if gm_tracker is not None:
                gm_tracker_display_string = await block_get_tracker(get_init_list(ctx, engine), guild.initiative, ctx,
                                                                    engine,
                                                                    bot,
                                                                    gm=True)
                gm_channel = bot.get_channel(gm_tracker_channel)
                gm_message = await gm_channel.fetch_message(gm_tracker)
                await gm_message.edit(gm_tracker_display_string)
        except NoResultFound as e:
            await ctx.channel.send(
                "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                "proper channel or run `/i admin setup` to setup the initiative tracker",
                delete_after=30)
        except Exception as e:
            print(f'update_pinned_tracker: {e}')
            report = ErrorReport(ctx, update_pinned_tracker.__name__, e, bot)
            await report.report()


async def block_post_init(ctx: discord.ApplicationContext, engine, bot):
    # Query the initiative position for the tracker and post it
    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            if guild.block:
                turn_list = await get_turn_list(ctx, engine, bot)
                block = True
                # print(f"block_post_init: \n {turn_list}")
            else:
                block = False

            init_list = get_init_list(ctx, engine)
            tracker_string = await block_get_tracker(init_list, guild.initiative, ctx, engine, bot)
            try:
                ping_string = ''
                if block:
                    for character in turn_list:
                        ping_string += f"<@{character[4]}>, it's your turn.\n"
                else:
                    ping_string = f"{ping_player_on_init(init_list, guild.initiative)}\n"
            except Exception as e:
                # print(f'post_init: {e}')
                ping_string = ''
        await ctx.send_followup(f"{tracker_string}\n"
                                f"{ping_string}")
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
                               delete_after=30)
    except Exception as e:
        print(f"block_post_init: {e}")
        report = ErrorReport(ctx, block_post_init.__name__, e, bot)
        await report.report()


# Note: Works backwards
async def get_turn_list(ctx: discord.ApplicationContext, engine, bot):
    turn_list = []
    block_done = False
    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            init_pos = guild.initiative
            init_list = get_init_list(ctx, engine)
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
                    if guild.round != 0:  # Don't loop back to the end on the first round
                        init_pos = length - 1
                    else:
                        block_done = True

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
                 unit: str,
                 auto_decrement: bool, bot):
    metadata = db.MetaData()
    insp = db.inspect(engine)
    # Get the Character's data
    try:
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
                # print(row)
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
                               delete_after=30)
        return False
    except Exception as e:
        print(f'set_cc: {e}')
        report = ErrorReport(ctx, set_cc.__name__, e, bot)
        await report.report()
        return False

    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()

            con = ConditionTable(ctx, metadata, engine).condition_table()
            if not insp.has_table(con.name):
                metadata.create_all(engine)

            if not guild.timekeeping or unit == 'Round':

                stmt = con.insert().values(
                    character_id=data[0][0],
                    title=title,
                    number=number,
                    counter=counter,
                    auto_increment=auto_decrement,
                    time=False
                )
                complied = stmt.compile()
                # print(complied)
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                await update_pinned_tracker(ctx, engine, bot)
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
                complied = stmt.compile()
                # print(complied)
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                await update_pinned_tracker(ctx, engine, bot)
                return True

    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
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
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
                # print(row)
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
                               delete_after=30)
        return False
    except Exception as e:
        print(f'edit_cc: {e}')
        report = ErrorReport(ctx, edit_cc.__name__, e, bot)
        await report.report()
        return False
    try:
        con = ConditionTable(ctx, metadata, engine).condition_table()
        stmt = update(con).where(con.c.character_id == data[0][0]).where(con.c.title == condition).values(
            number=value
        )
        complied = stmt.compile()
        # print(complied)
        con_data = []
        with engine.connect() as conn:
            result = conn.execute(stmt)
        await update_pinned_tracker(ctx, engine, bot)
        return True
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
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
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
                # print(row)
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
                               delete_after=30)
        return False
    except Exception as e:
        print(f'delete_cc: {e}')
        report = ErrorReport(ctx, delete_cc.__name__, e, bot)
        await report.report()
        return False

    try:
        con = ConditionTable(ctx, metadata, engine).condition_table()
        stmt = delete(con).where(con.c.character_id == data[0][0]).where(con.c.title == condition)
        complied = stmt.compile()
        # print(complied)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # print(result)
        await update_pinned_tracker(ctx, engine, bot)
        return True
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
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
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
                # print(row)
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
                               delete_after=30)
        return False
    except Exception as e:
        print(f'get_cc: {e}')
        report = ErrorReport(ctx, get_cc.__name__, e, bot)
        await report.report()

    try:
        con = ConditionTable(ctx, metadata, engine).condition_table()
        stmt = con.select().where(con.c.character_id == data[0][0]).where(con.c.counter == True)
        complied = stmt.compile()
        # print(complied)
        con_data = []
        with engine.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                con_data.append(row)
        return con_data
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
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
    con = ConditionTable(ctx, metadata, engine).condition_table()
    emp = TrackerTable(ctx, metadata, engine).tracker_table()
    stmt = con.select().where(con.c.time == True)
    with engine.connect() as conn:
        for row in conn.execute(stmt):
            time_stamp = datetime.datetime.fromtimestamp(row[4])
            time_left = time_stamp - current_time
            if time_left.total_seconds() <= 0:
                char_stmt = emp.select().where(emp.c.id == row[1])
                char_name = ''
                for char_row in conn.execute(char_stmt):
                    char_name = char_row[1]
                del_stmt = delete(con).where(con.c.id == row[0])
                await ctx.channel.send(f"{row[3]} removed from {char_name}")
                result = conn.execute(del_stmt)


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# UTILITY FUNCTIONS

# Checks to see if the user of the slash command is the GM, returns a boolean
def gm_check(ctx, engine):
    with Session(engine) as session:
        guild = session.execute(select(Global).filter(
            or_(
                Global.tracker_channel == ctx.interaction.channel_id,
                Global.gm_tracker_channel == ctx.interaction.channel_id
            )
        )
        ).scalar_one()
        if int(guild.gm) != int(ctx.interaction.user.id):
            return False
        else:
            return True


async def player_check(ctx: discord.ApplicationContext, engine, bot, character: str):
    metadata = db.MetaData()
    try:
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = select(emp.c.player).where(emp.c.name == character)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
        return data[0]
    except Exception as e:
        print(f'player_check: {e}')
        report = ErrorReport(ctx, player_check.__name__, e, bot)
        await report.report()


#############################################################################
#############################################################################
# SLASH COMMANDS
# The Initiative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.lock = asyncio.Lock()
        self.update_status.start()

    # Update the bot's status periodically
    @tasks.loop(minutes=1)
    async def update_status(self):
        with Session(self.engine) as session:
            result = session.query(Global).count()
        async with self.lock:
            await self.bot.change_presence(activity=discord.Game(name=f"ttRPGs in {result} tables across the "
                                                                      f"digital universe."))
            # f"Playing ttRPGs in {result} tables across the digital universe."

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

        with Session(self.engine) as session:
            gm_status = gm_check(ctx, self.engine)

        try:
            emp = TrackerTable(ctx, metadata, self.engine).tracker_table()
            stmt = emp.select()
            compiled = stmt.compile()
            # print(compiled)
            with self.engine.connect() as conn:
                data = []
                for row in conn.execute(stmt):
                    data.append(row)
                    # print(row)
            for row in data:
                # if row[4] == ctx.interaction.user.id or gm_status:
                character_list.append(row[1])
            # print(character_list)
            return character_list
        except Exception as e:
            print(f'character+select: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return False

    # Autocomplete to return the list of character the user owns, or all if the user is the GM
    async def character_select_gm(self, ctx: discord.AutocompleteContext):
        metadata = db.MetaData()
        character_list = []

        with Session(self.engine) as session:
            gm_status = gm_check(ctx, self.engine)

        try:
            emp = TrackerTable(ctx, metadata, self.engine).tracker_table()
            stmt = emp.select()
            compiled = stmt.compile()
            # print(compiled)
            with self.engine.connect() as conn:
                data = []
                for row in conn.execute(stmt):
                    data.append(row)
                    # print(row)
            for row in data:
                if row[4] == ctx.interaction.user.id or gm_status:
                    character_list.append(row[1])
            # print(character_list)
            return character_list
        except Exception as e:
            print(f'character+select: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return False

    async def cc_select(self, ctx: discord.AutocompleteContext):
        metadata = db.MetaData()
        character = ctx.options['character']
        con = ConditionTable(ctx, metadata, self.engine).condition_table()
        emp = TrackerTable(ctx, metadata, self.engine).tracker_table()

        char_stmt = emp.select().where(emp.c.name == character)
        # print(character)
        with self.engine.connect() as conn:
            data = []
            con_list = []
            for char_row in conn.execute(char_stmt):
                data.append(char_row)
            for row in data:
                # print(row)
                con_stmt = con.select().where(con.c.character_id == row[0])
                for char_row in conn.execute(con_stmt):
                    # print(char_row)
                    con_list.append(f"{char_row[3]}")
        return con_list

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Slash commands

    i = SlashCommandGroup("i", "Initiative Tracker")

    @i.command(description="Administrative Commands",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    @option('mode', choices=['setup', 'transfer gm', 'reset trackers'])
    @option('gm', description="@Player to transfer GM permissions to.")
    @option('channel', description="Player Channel")
    @option('gm_channel', description="GM Channel")
    async def admin(self, ctx: discord.ApplicationContext, mode: str,
                    gm: discord.User = discord.ApplicationContext.user,
                    channel: discord.TextChannel = discord.ApplicationContext.channel,
                    gm_channel: discord.TextChannel = None):
        if mode == 'setup':
            response = await setup_tracker(ctx, self.engine, self.bot, gm, channel, gm_channel)
            if response:
                await ctx.respond("Server Setup", ephemeral=True)
                return
            else:
                # await ctx.respond("Server Setup Failed. Perhaps it has already been set up?", ephemeral=True)
                return

        if not gm_check(ctx, self.engine):
            await ctx.respond("GM Restricted Command", ephemeral=True)
            return
        else:
            try:
                if mode == 'reset trackers':
                    await ctx.response.defer(ephemeral=True)
                    response = await repost_trackers(ctx, self.engine, self.bot)
                    if response:
                        await ctx.send_followup("Trackers Placed",
                                                ephemeral=True)
                    else:
                        await ctx.send_followup("Error setting trackers")

                elif mode == 'transfer gm':
                    response = await set_gm(ctx, gm, self.engine, self.bot)
                    if response:
                        await ctx.respond(f"GM Permissions transferred to {gm.mention}")
                    else:
                        await ctx.respond("Permission Transfer Failed", ephemeral=True)
                else:
                    await ctx.respond("Failed. Check your syntax and spellings.", ephemeral=True)
            except NoResultFound as e:
                await ctx.respond(
                    "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                    "proper channel or run `/i admin setup` to setup the initiative tracker", ephemeral=True)
            except Exception as e:
                print(f"/i admin: {e}")
                report = ErrorReport(ctx, "slash command /i admin", e, self.bot)
                await report.report()

    @i.command(description="Add PC on NPC",
               # guild_ids=[GUILD]
               )
    @option('name', description="Character Name")
    @option('hp', description='Total HP')
    @option('player', choices=['player', 'npc'])
    @option('initiative', description="Set Init (Number or XdY+Z)")
    async def add(self, ctx: discord.ApplicationContext, name: str, hp: int, player: str, initiative: str = 0):
        response = False
        player_bool = False
        if player == 'player':
            player_bool = True
        elif player == 'npc':
            player_bool = False

        response = await add_character(ctx, self.engine, self.bot, name, hp, player_bool, initiative)
        if not response:
            await ctx.respond(f"Error Adding Character", ephemeral=True)

        await update_pinned_tracker(ctx, self.engine, self.bot)

    @i.command(description="Manage Initiative",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    @option('mode', choices=['start', 'stop', 'delete character'])
    @option('character', description='Character to delete')
    async def manage(self, ctx: discord.ApplicationContext, mode: str, character: str = ''):
        init_list = get_init_list(ctx, self.engine)
        try:
            with Session(self.engine) as session:
                guild = session.execute(select(Global).filter(
                    or_(
                        Global.tracker_channel == ctx.channel.id,
                        Global.gm_tracker_channel == ctx.channel.id
                    )
                )
                ).scalar_one()
                if not gm_check(ctx, self.engine):
                    await ctx.respond("GM Restricted Command", ephemeral=True)
                    return
                else:
                    if mode == 'start':
                        await ctx.response.defer()
                        await block_advance_initiative(ctx, self.engine, self.bot)
                        await block_post_init(ctx, self.engine, self.bot)
                        await update_pinned_tracker(ctx, self.engine, self.bot)
                        # await ctx.respond('Initiative Started', ephemeral=True)
                    elif mode == 'stop':
                        await ctx.response.defer()
                        guild.initiative = None
                        guild.saved_order = ''
                        metadata = db.MetaData()
                        con = ConditionTable(ctx, metadata, self.engine).condition_table()
                        stmt = delete(con).where(con.c.counter == False).where(con.c.auto_increment == True).where(
                            con.c.time == False)
                        compiled = stmt.compile()
                        with self.engine.connect() as conn:
                            result = conn.execute(stmt)
                            # print(result)
                        await update_pinned_tracker(ctx, self.engine, self.bot)
                        session.commit()

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
        except NoResultFound as e:
            await ctx.respond(
                "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                "proper channel or run `/i admin setup` to setup the initiative tracker",
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
        result = False  # set fail state
        try:

            init_list = get_init_list(ctx, self.engine)
            with Session(self.engine) as session:
                guild = session.execute(select(Global).filter(
                    or_(
                        Global.tracker_channel == ctx.channel.id,
                        Global.gm_tracker_channel == ctx.channel.id
                    )
                )
                ).scalar_one()
                await ctx.response.defer()
                # Advance Init and Display
                await block_advance_initiative(ctx, self.engine, self.bot)  # Advance the init

                # Query the initiative position for the tracker and post it
                await block_post_init(ctx, self.engine, self.bot)
                await update_pinned_tracker(ctx, self.engine, self.bot)  # update the pinned tracker
        except NoResultFound as e:
            await ctx.respond("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                              "proper channel or run `/i admin setup` to setup the initiative tracker", ephemeral=True)
        except Exception as e:
            print(f"/i next: {e}")
            report = ErrorReport(ctx, "slash command /i next", e, self.bot)
            await report.report()

    @i.command(description="Set Init (Number or XdY+Z)",
               # guild_ids=[GUILD]
               )
    @option("character", description="Character to select", autocomplete=character_select_gm, )
    async def init(self, ctx: discord.ApplicationContext, character: str, init: str):
        with Session(self.engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            # print(guild)
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
                    roll = dice.plain_roll(init)
                    success = await set_init(ctx, self.bot, character, roll[1], self.engine)
                    if success:
                        await ctx.respond(f"Initiative set to {roll[0]} = {roll[1]} for {character}")
                    else:
                        await ctx.respond("Failed to set initiative.", ephemeral=True)
            await update_pinned_tracker(ctx, self.engine, self.bot)

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

    @i.command(description="Add conditions and counters",
               # guild_ids=[GUILD]
               )
    @option("character", description="Character to select", autocomplete=character_select)
    @option('type', choices=['Condition', 'Counter'])
    @option('auto', description="Auto Decrement", choices=['Auto Decrement', 'Static'])
    @option('unit', choices=['Round', 'Minute', 'Hour', 'Day'])
    async def cc(self, ctx: discord.ApplicationContext, character: str, title: str, type: str, number: int = None,
                 unit: str = "Round",
                 auto: str = 'Static'):
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
            await ctx.respond("Success", ephemeral=True)
        else:
            await ctx.respond("Failure", ephemeral=True)

    @i.command(description="Edit or remove conditions and counters",
               # guild_ids=[GUILD]
               )
    @option('mode', choices=['edit', 'delete'])
    @option("character", description="Character to select", autocomplete=character_select)
    @option("condition", description="Condition", autocomplete=cc_select)
    async def cc_edit(self, ctx: discord.ApplicationContext, mode: str, character: str, condition: str,
                      new_value: int = 0):
        result = False
        if mode == 'delete':
            result = await delete_cc(ctx, self.engine, character, condition, self.bot)
            await ctx.respond(f"{condition} on {character} deleted.", ephemeral=True)
        elif mode == 'edit':
            result = await edit_cc(ctx, self.engine, character, condition, new_value, self.bot)
            await ctx.respond(f"{condition} on {character} updated.", ephemeral=True)
        else:
            await ctx.respond("Failed", ephemeral=True)

        if not result:
            await ctx.respond("Failed", ephemeral=True)

    @i.command(description="Show Custom Counters")
    @option("character", description="Character to select", autocomplete=character_select_gm)
    async def cc_show(self, ctx: discord.ApplicationContext, character: str):
        await ctx.response.defer(ephemeral=True)
        try:
            if not await player_check(ctx, self.engine, self.bot, character) and not gm_check(ctx, self.engine):
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
