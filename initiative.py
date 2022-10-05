# initiative.py
# Initiative Tracker Module

import os

# imports
import discord
import sqlalchemy as db
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from sqlalchemy import union_all, and_, or_

from database_models import Global, Base, TrackerTable, ConditionTable
from database_operations import get_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport
from time_keeping_functions import output_datetime, check_timekeeper, advance_time

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

# Set up the tracker if it does not exit.db
async def setup_tracker(ctx: discord.ApplicationContext, engine, bot, gm: discord.User, channel: discord.TextChannel,
                        gm_channel: discord.TextChannel):
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
            display_string = await get_tracker(get_init_list(ctx, engine), init_pos, ctx, engine,
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


# Add a character to the database
async def add_character(ctx: discord.ApplicationContext, engine, bot, name: str, hp: int, player_bool: bool):
    metadata = db.MetaData()
    try:
        emp = TrackerTable(ctx, metadata, engine).tracker_table()
        stmt = emp.insert().values(
            name=name,
            init=0,
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


async def advance_initiative(ctx: discord.ApplicationContext, engine, bot):
    metadata = db.MetaData()
    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            if guild.initiative is None:
                init_pos = -1
            else:
                init_pos = int(guild.initiative)

            if guild.saved_order == '':
                current_character = get_init_list(ctx, engine)[0]
            else:
                current_character = guild.saved_order
            # make sure that the current character is at the same place in initiative as it was before

            # decrement any conditions with the decrement flag
            try:
                emp = TrackerTable(ctx, metadata, engine).tracker_table()
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
                report = ErrorReport(ctx, advance_initiative.__name__, e, bot)
                await report.report()
                return False

            try:
                con = ConditionTable(ctx, metadata, engine).condition_table()
                stmt = con.select().where(con.c.character_id == data[0][0])
                compiled = stmt.compile()
                with engine.connect() as conn:
                    for con_row in conn.execute(stmt):
                        if con_row[5]:
                            if con_row[4] >= 2:
                                new_stmt = update(con).where(con.c.id == con_row[0]).values(
                                    number=con_row[4] - 1
                                )
                            else:
                                new_stmt = delete(con).where(con.c.id == con_row[0])
                            result = conn.execute(new_stmt)
            except Exception as e:
                print(f'advance_initiative: {e}')
                report = ErrorReport(ctx, advance_initiative.__name__, e, bot)
                await report.report()

            # if its not, set the init position to the position of the current character before advancing it
            if not init_integrity_check(ctx, init_pos, current_character, engine):
                for pos, row in enumerate(get_init_list(ctx, engine)):
                    if row[1] == current_character:
                        init_pos = pos

            init_pos += 1  # increase the init position by 1
            if init_pos >= len(get_init_list(ctx, engine)):  # if it has reached the end, loop back to the beginning
                init_pos = 0
                if guild.timekeeping:                    # if timekeeping is enable on the server
                    # Advance time time by the number of seconds in the guild.time column. Default is 6
                    # seconds ala D&D standard
                    await advance_time(ctx, engine, bot, second=guild.time)
            guild.initiative = init_pos  # set it
            guild.saved_order = str(get_init_list(ctx, engine)[init_pos][1])
            session.commit()



            return True
    except Exception as e:
        print(f"advance_initiative: {e}")
        report = ErrorReport(ctx, advance_initiative.__name__, e, bot)
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


# Build the tracker string
async def get_tracker(init_list: list, selected: int, ctx: discord.ApplicationContext, engine, bot, gm: bool = False):
    # Get the datetime
    datetime_string = ''
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
            if x == selected:
                selector = '>>'
            else:
                selector = ''
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
        print(f"get_tracker: {e}")
        report = ErrorReport(ctx, get_tracker.__name__, e, bot)
        await report.report()


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


async def set_cc(ctx: discord.ApplicationContext, engine, character: str, title: str, counter: bool, number: int,
                 auto_decrement: bool, bot):
    metadata = db.MetaData()
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
        con = ConditionTable(ctx, metadata, engine).condition_table()
        stmt = con.insert().values(
            character_id=data[0][0],
            title=title,
            number=number,
            counter=counter,
            auto_increment=auto_decrement
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
                tracker_display_string = await get_tracker(get_init_list(ctx, engine), guild.initiative, ctx, engine,
                                                           bot)
                channel = bot.get_channel(tracker_channel)
                message = await channel.fetch_message(tracker)
                await message.edit(tracker_display_string)

            # Update the GM tracker
            if gm_tracker is not None:
                gm_tracker_display_string = await get_tracker(get_init_list(ctx, engine), guild.initiative, ctx, engine,
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


async def post_init(ctx: discord.ApplicationContext, engine, bot):
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
            init_list = get_init_list(ctx, engine)
            tracker_string = await get_tracker(init_list, guild.initiative, ctx, engine, bot)
            try:
                ping_string = ping_player_on_init(init_list, guild.initiative)
            except Exception as e:
                print(f'post_init: {e}')
                ping_string = ''
        await ctx.send_followup(f"{tracker_string}\n"
                                f"{ping_string}")
    except NoResultFound as e:
        await ctx.channel.send("The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                               "proper channel or run `/i admin setup` to setup the initiative tracker",
                               delete_after=30)
    except Exception as e:
        print(f"post_init: {e}")
        report = ErrorReport(ctx, post_init.__name__, e, bot)
        await report.report()


# Checks to see if the user of the slash command is the GM, returns a boolean
def gm_check(ctx: discord.ApplicationContext, engine):
    with Session(engine) as session:
        guild = session.execute(select(Global).filter(
            or_(
                Global.tracker_channel == ctx.channel.id,
                Global.gm_tracker_channel == ctx.channel.id
            )
        )
        ).scalar_one()
        if int(guild.gm) != int(ctx.user.id):
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

    i = SlashCommandGroup("i", "Initiative Tracker")

    @i.command(description="Administrative Commands",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    @option('mode', choices=['setup', 'transfer gm', 'gm tracker'])
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
                await ctx.respond("Server Setup Failed. Perhaps it has already been set up?", ephemeral=True)
                return

        if not gm_check(ctx, self.engine):
            await ctx.respond("GM Restricted Command", ephemeral=True)
            return
        else:
            try:
                if mode == 'gm tracker':
                    await ctx.response.defer(ephemeral=True)
                    response = set_pinned_tracker(ctx, self.engine, self.bot, ctx.channel, gm=True)
                    if response:
                        await ctx.send_followup("Tracker Placed",
                                                ephemeral=True)
                    else:
                        await ctx.send_followup("Error setting tracker")

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
    async def add(self, ctx: discord.ApplicationContext, name: str, hp: int, player: str):
        response = False
        player_bool = False
        if player == 'player':
            player_bool = True
        elif player == 'npc':
            player_bool = False

        response = await add_character(ctx, self.engine, self.bot, name, hp, player_bool)
        if response:
            await ctx.respond(f"Character {name} added successfully", ephemeral=True)
        else:
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
                        guild.initiative = 0
                        guild.saved_order = parse_init_list(init_list)[0]
                        session.commit()
                        await post_init(ctx, self.engine, self.bot)
                        await update_pinned_tracker(ctx, self.engine, self.bot)
                        # await ctx.respond('Initiative Started', ephemeral=True)
                    elif mode == 'stop':
                        await ctx.response.defer()
                        guild.initiative = None
                        guild.saved_order = ''
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
                # If initiative has not been started, start it, if not advance the init
                if guild.initiative is None:
                    await ctx.response.defer()
                    guild.initiative = 0
                    guild.saved_order = parse_init_list(init_list)[0]
                    session.commit()
                    await post_init(ctx, self.engine, self.bot)
                    await update_pinned_tracker(ctx, self.engine, self.bot)
                else:
                    # Advance Init and Display
                    result = await advance_initiative(ctx, self.engine, self.bot)  # Advance the init

                    # Query the initiative position for the tracker and post it
                    await ctx.response.defer()
                    await post_init(ctx, self.engine, self.bot)
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
    @option('name', description="Character Name")
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
    @option('type', choices=['Condition', 'Counter'])
    @option('auto', description="Auto Decrement", choices=['Auto Decrement', 'Static'])
    async def cc(self, ctx: discord.ApplicationContext, character: str, title: str, type: str, number: int = None,
                 auto: str = 'Static'):
        if type == "Condition":
            counter_bool = False
        else:
            counter_bool = True
        if auto == 'Auto Decrement':
            auto_bool = True
        else:
            auto_bool = False

        response = await set_cc(ctx, self.engine, character, title, counter_bool, number, auto_bool, self.bot)
        if response:
            await ctx.respond("Success", ephemeral=True)
        else:
            await ctx.respond("Failure", ephemeral=True)

    @i.command(description="Edit or remove conditions and counters",
               # guild_ids=[GUILD]
               )
    @option('mode', choices=['edit', 'delete'])
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
