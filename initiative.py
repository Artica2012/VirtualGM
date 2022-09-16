# initiative.py
# Initiative Tracker Module

# imports
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from discord import option
from discord.ext import tasks

import sqlalchemy as db
from sqlalchemy import create_engine, event, insert
from database_models import Global, Base, TrackerTable, ConditionTable
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from dice_roller import DiceRoller
from database_operations import get_db_engine

import os
from dotenv import load_dotenv

# define global variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
USERNAME = os.getenv('Username')
PASSWORD = os.getenv('Password')
HOSTNAME = os.getenv('Hostname')
PORT = os.getenv('PGPort')


#################################################################
#################################################################
# FUNCTIONS

# Set up the tracker if it does not exit.db
def setup_tracker(server: discord.Guild, user: discord.User):
    try:
        # engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        conn = engine.connect()
        metadata = db.MetaData()
        emp = TrackerTable(server, metadata).tracker_table()
        con = ConditionTable(server, metadata).condition_table()
        metadata.create_all(engine)
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            guild = Global(
                guild_id=server.id,
                time=0,
                gm=user.id,
            )
            session.add(guild)
            session.commit()

        return True

    except Exception as e:
        print(e)
        return False


def set_gm(server: discord.Guild, new_gm: discord.User):
    try:
        # engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        conn = engine.connect()
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=server.id)).scalar_one()
            guild.gm = new_gm.id
            session.commit()

        return True
    except Exception as e:
        print(e)
        return False


# Add a player to the database
def add_player(name: str, user: int, server: discord.Guild, HP: int):
    # engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(server, metadata).tracker_table()
        stmt = emp.insert().values(
            name=name,
            init=0,
            player=True,
            user=user,
            current_hp=HP,
            max_hp=HP,
            temp_hp=0
        )
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # conn.commit()
        return True
    except Exception as e:
        print(e)
        return False


# Add an NPC to the database
def add_npc(name: str, user: int, server: discord.Guild, HP: int):
    # engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(server, metadata).tracker_table()
        stmt = emp.insert().values(
            name=name,
            init=0,
            player=False,
            user=user,
            current_hp=HP,
            max_hp=HP,
            temp_hp=0
        )
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # conn.commit()
        return True
    except Exception as e:
        print(e)
        return False


def delete_character(server: discord.Guild, name: str):
    # engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(server, metadata).tracker_table()
        stmt = delete(emp).where(emp.c.name == name)
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # conn.commit()
        return True
    except Exception as e:
        print(e)
        return False


# Set the initiative
def set_init(server: discord.Guild, name: str, init: int):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(server, metadata).tracker_table()
        stmt = update(emp).where(emp.c.name == name).values(
            init=init
        )
        compiled = stmt.compile()
        print(compiled)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # conn.commit()
            if result.rowcount == 0:
                print("RowCount = 0")
                return False
        return True
    except Exception as e:
        print(e)
        return False


def init_integrity_check(server: discord.Guild, init_pos: int, current_character: str):
    init_list = get_init_list(server)
    if init_list[init_pos][1] == current_character:
        return True
    else:
        return False


def advance_initiative(server: discord.Guild):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    # try:
    with Session(engine) as session:
        # get current position in the initiative
        guild = session.execute(select(Global).filter_by(guild_id=server.id)).scalar_one()
        if guild.initiative is None:
            init_pos = -1
        else:
            init_pos = int(guild.initiative)

        if guild.saved_order == '':
            current_character = get_init_list(server)[0]
        else:
            current_character = guild.saved_order
        # make sure that the current character is at the same place in initiative as it was before

        # decrement any conditions with the decrement flag
        try:
            emp = TrackerTable(server, metadata).tracker_table()
            stmt = emp.select().where(emp.c.name == current_character)
            compiled = stmt.compile()
            # print(compiled)
            with engine.connect() as conn:
                data = []
                for row in conn.execute(stmt):
                    data.append(row)
                    # print(row)
        except Exception as e:
            # print(e)
            return False

        try:
            con = ConditionTable(server, metadata).condition_table()
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
            print(e)

        # if its not, set the init position to the position of the current character before advancing it
        if not init_integrity_check(server, init_pos, current_character):
            for pos, row in enumerate(get_init_list(server)):
                if row[1] == current_character:
                    init_pos = pos

        init_pos += 1
        if init_pos >= len(get_init_list(server)):
            init_pos = 0
        guild.initiative = init_pos
        print(get_init_list(server)[init_pos])
        guild.saved_order = str(get_init_list(server)[init_pos][1])
        session.commit()

        return True
    # except Exception as e:
    #     return False


def get_init_list(server: discord.Guild):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    emp = TrackerTable(server, metadata).tracker_table()
    stmt = emp.select().order_by(emp.c.init.desc())
    # print(stmt)
    data = []
    with engine.connect() as conn:
        for row in conn.execute(stmt):
            # print(row)
            data.append(row)
        # print(data)
        return data


def parse_init_list(server: discord.Guild, init_list: list):
    parsed_list = []
    for row in init_list:
        parsed_list.append(row[1])
    return parsed_list


def ping_player_on_init(init_list: list, selected: int):
    selected_char = init_list[selected]
    user = selected_char[4]
    return f"<@{user}>, it's your turn."


def get_tracker(init_list: list, selected: int, ctx: discord.ApplicationContext, gm: bool = False):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    con = ConditionTable(ctx.guild, metadata).condition_table()
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

    output_string = "```" \
                    "Initiative:\n"
    for x, row in enumerate(row_data):
        if x == selected:
            selector = '>>'
        else:
            selector = ''
        if row['player']:
            if row['thp'] != 0:
                string = f"{selector} {row['init']} {str(row['name']).title()}: {row['chp']}/{row['maxhp']} ({row['thp']}) Temp\n"
            else:
                string = f"{selector}  {row['init']} {str(row['name']).title()}: {row['chp']}/{row['maxhp']}\n"
        else:
            hp_string = calculate_hp(row['chp'], row['maxhp'])
            string = f"{selector}  {row['init']} {str(row['name']).title()}: {hp_string} \n"
        output_string += string

        for con_row in row['cc']:
            if not con_row[2]:
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
    print(output_string)
    return output_string


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


def add_thp(server: discord.Guild, name: str, ammount: int):
    # engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(server, metadata).tracker_table()
        stmt = emp.select().where(emp.c.name == name)
        compiled = stmt.compile()
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)

        thp = data[0][7]
        new_thp = thp + ammount

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
        print(e)
        return False


def change_hp(server: discord.Guild, name: str, ammount: int, heal: bool):
    # engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(server, metadata).tracker_table()
        stmt = emp.select().where(emp.c.name == name)
        compiled = stmt.compile()
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)

        chp = data[0][5]
        maxhp = data[0][6]
        thp = data[0][7]
        new_thp = 0

        if heal:
            new_hp = chp + ammount
            if new_hp > maxhp:
                new_hp = maxhp
        if not heal:
            if thp == 0:
                new_hp = chp - ammount
                if new_hp < 0:
                    new_hp - 0
            else:
                if thp > ammount:
                    new_thp = thp - ammount
                    new_hp = chp
                else:
                    new_thp = 0
                    new_hp = chp - ammount + thp
                    if new_hp < 0:
                        new_hp = 0

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
        print(e)
        return False


async def set_cc(ctx: discord.ApplicationContext, character: str, title: str, counter: bool, number: int,
                 auto_decrement: bool, bot):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    # Get the Character's data
    try:
        emp = TrackerTable(ctx.guild, metadata).tracker_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
                # print(row)
    except Exception as e:
        # print(e)
        return False

    try:
        con = ConditionTable(ctx.guild, metadata).condition_table()
        stmt = con.insert().values(
            character_id=data[0][0],
            title=title,
            number=number,
            counter=counter,
            auto_increment=auto_decrement
        )
        complied = stmt.compile()
        print(complied)
        with engine.connect() as conn:
            result = conn.execute(stmt)
        await update_pinned_tracker(ctx, engine, bot)
        return True
    except Exception as e:
        print(e)
        return False


async def edit_cc(ctx: discord.ApplicationContext, character: str, condition: str, value: int, bot):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(ctx.guild, metadata).tracker_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
                # print(row)
    except Exception as e:
        print(e)
        return False
    try:
        con = ConditionTable(ctx.guild, metadata).condition_table()
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
    except Exception as e:
        print(e)
        return False


async def delete_cc(ctx: discord.ApplicationContext, character: str, condition, bot):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(ctx.guild, metadata).tracker_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
                # print(row)
    except Exception as e:
        # print(e)
        return False

    try:
        con = ConditionTable(ctx.guild, metadata).condition_table()
        stmt = delete(con).where(con.c.character_id == data[0][0]).where(con.c.title == condition)
        complied = stmt.compile()
        print(complied)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            # print(result)
        await update_pinned_tracker(ctx, engine, bot)
        return True
    except Exception as e:
        print(e)
        return False

def get_cc(ctx: discord.ApplicationContext, character: str):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        emp = TrackerTable(ctx.guild, metadata).tracker_table()
        stmt = emp.select().where(emp.c.name == character)
        compiled = stmt.compile()
        # print(compiled)
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)
                # print(row)
    except Exception as e:
        print(e)
    try:
        con = ConditionTable(ctx.guild, metadata).condition_table()
        stmt = con.select().where(con.c.character_id == data[0][0]).where(con.c.counter == True)
        complied = stmt.compile()
        # print(complied)
        con_data = []
        with engine.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                con_data.append(row)
        return con_data
    except Exception as e:
        print(e)



async def update_pinned_tracker(ctx, engine, bot):
    with Session(engine) as session:
        try:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild_id)).scalar_one()
            tracker = guild.tracker
            tracker_channel = guild.tracker_channel
            tracker_display_string = get_tracker(get_init_list(ctx.guild), guild.initiative, ctx)
            channel = bot.get_channel(tracker_channel)
            message = await channel.fetch_message(tracker)
            await message.edit(tracker_display_string)
        except Exception as e:
            pass


async def post_init(ctx: discord.ApplicationContext, engine):
    # Query the initiative position for the tracker and post it
    with Session(engine) as session:
        guild = session.execute(select(Global).filter_by(guild_id=ctx.guild.id)).scalar_one()
        init_list = get_init_list(ctx.guild)
        tracker_string = get_tracker(init_list, guild.initiative, ctx)
        ping_string = ping_player_on_init(init_list, guild.initiative)
    await ctx.send_followup(f"{tracker_string}\n"
                            f"{ping_string}")


#############################################################################
#############################################################################
# SLASH COMMANDS
# The Initiative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    i = SlashCommandGroup("i", "Initiative Tracker")

    @i.command(description="Administrative Commands",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    @option('mode', choices=['setup', 'delete', 'tracker'])
    async def admin(self, ctx: discord.ApplicationContext, mode: str, argument: str = ''):
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        if mode == 'setup':
            response = setup_tracker(ctx.guild, ctx.user)
            if response:
                await ctx.respond("Server Setup", ephemeral=True)
                return
            else:
                await ctx.respond("Server Setup Failed. Perhaps it has already been set up?", ephemeral=True)
                return

        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild_id)).scalar_one()
            if int(guild.gm) != int(ctx.user.id):
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            if mode == 'delete':
                if argument == guild.saved_order:
                    await ctx.respond(f"Please wait until {argument} is not the active character in initiative before "
                                      f"deleting it.", ephemeral=True)
                else:
                    delete_character(ctx.guild, argument)
                    await ctx.respond(f'{argument} deleted', ephemeral=True)
                    await update_pinned_tracker(ctx, engine, self.bot)
            elif mode == 'tracker':
                try:
                    init_pos = int(guild.initiative)
                except Exception as e:
                    init_pos = None
                display_string = get_tracker(get_init_list(ctx.guild), init_pos, ctx)
                # interaction = await ctx.respond(display_string)
                interaction = await ctx.channel.send(display_string)
                await ctx.respond("Tracker Placed",
                                  ephemeral=True)
                await interaction.pin()
                guild.tracker = interaction.id
                guild.tracker_channel = ctx.channel.id
                session.commit()
            else:
                await ctx.respond("Failed. Check your syntax and spellings.", ephemeral=True)

    @i.command(description="Transfer GM duties to a new player",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    async def transfer_gm(self, ctx: discord.ApplicationContext, new_gm: discord.User):
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild_id)).scalar_one()
            if int(guild.gm) != int(ctx.user.id):
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            response = set_gm(ctx.guild, new_gm)
            if response:
                await ctx.respond(f"GM Permissions transferred to {new_gm.mention}")
            else:
                await ctx.respond("Permission Transfer Failed", ephemeral=True)

    @i.command(description="Add PC on NPC",
               # guild_ids=[GUILD]
               )
    @option('name', description="Character Name")
    @option('hp', description='Total HP')
    @option('player', choices=['player', 'npc'])
    async def add(self, ctx: discord.ApplicationContext, name: str, hp: int, player: str):
        if player == 'player':
            response = add_player(name, ctx.user.id, ctx.guild, hp)
            if response:
                await ctx.respond(f"Character {name} added successfully", ephemeral=True)
            else:
                await ctx.respond(f"Error Adding Character", ephemeral=True)
        elif player == 'npc':
            response = add_npc(name, ctx.user.id, ctx.guild, hp)
            if response:
                await ctx.respond(f"Character {name} added successfully", ephemeral=True)
            else:
                await ctx.respond(f"Error Adding Character", ephemeral=True)
        else:
            await ctx.respond('Failed.', ephemeral=True)
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await update_pinned_tracker(ctx, engine, self.bot)

    @i.command(description="Start/Stop Initiative",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    @option('mode', choices=['start', 'stop'])
    async def manage(self, ctx: discord.ApplicationContext, mode: str):
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        init_list = get_init_list(ctx.guild)

        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild_id)).scalar_one()
            if int(guild.gm) != int(ctx.user.id):
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            if mode == 'start':
                await ctx.response.defer()
                guild.initiative = 0
                guild.saved_order = parse_init_list(ctx.guild, init_list)[0]
                session.commit()
                await post_init(ctx, engine)
                await update_pinned_tracker(ctx, engine, self.bot)
                # await ctx.respond('Initiative Started', ephemeral=True)
            elif mode == 'stop':
                await ctx.response.defer()
                guild.initiative = None
                guild.saved_order = ''
                session.commit()
                await update_pinned_tracker(ctx, engine, self.bot)
                await ctx.send_followup("Initiative Ended.")

    @i.command(description="Advance Initiative",
               # guild_ids=[GUILD]
               )
    async def next(self, ctx: discord.ApplicationContext):
        # Initialize engine
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        result = False  # set fail state

        # Advance Init and Display
        result = advance_initiative(ctx.guild)  # Advance the init

        # Query the initiative position for the tracker and post it
        await ctx.response.defer()
        await post_init(ctx, engine)
        await update_pinned_tracker(ctx, engine, self.bot)  # update the pinned tracker
        # await ctx.respond("New Turn")

    @i.command(description="Set Init (Number of XdY+Z",
               # guild_ids=[GUILD]
               )
    async def init(self, ctx: discord.ApplicationContext, character: str, init: str):
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild_id)).scalar_one()
            # print(guild)
            if character == guild.saved_order:
                await ctx.respond(f"Please wait until {character} is not the active character in initiative before "
                                  f"resetting its initiative.", ephemeral=True)
            else:
                dice = DiceRoller('')
                try:
                    print(f"Init: {init}")
                    initiative = int(init)
                    success = set_init(ctx.guild, character, initiative)
                    if success:
                        await ctx.respond(f"Initiative set to {initiative} for {character}")
                    else:
                        await ctx.respond("Failed to set initiative.", ephemeral=True)
                except:
                    roll = dice.plain_roll(init)
                    success = set_init(ctx.guild, character, roll[1])
                    if success:
                        await ctx.respond(f"Initiative set to {roll[0]} = {roll[1]} for {character}")
                    else:
                        await ctx.respond("Failed to set initiative.", ephemeral=True)
        await update_pinned_tracker(ctx, engine, self.bot)

    @i.command(description="Heal, Damage or add Temp HP",
               # guild_ids=[GUILD]
               )
    @option('name', description="Character Name")
    @option('mode', choices=['Damage', 'Heal', "Temporary HP"])
    async def hp(self, ctx: discord.ApplicationContext, name: str, mode: str, amount: int):
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        if mode == 'Heal':
            response = change_hp(ctx.guild, name, amount, True)
            if response:
                await ctx.respond(f"{name} healed for {amount}.")
        elif mode == 'Damage':
            response = change_hp(ctx.guild, name, amount, False)
            if response:
                await ctx.respond(f"{name} damaged for {amount}.")
        elif mode == 'Temporary HP':
            response = add_thp(ctx.guild, name, amount)
            if response:
                await ctx.respond(f"{amount} Temporary HP added to {name}.")
        if not response:
            await ctx.respond("Failed", ephemeral=True)
        await update_pinned_tracker(ctx, engine, self.bot)

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

        response = await set_cc(ctx, character, title, counter_bool, number, auto_bool, self.bot)
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
            result = await delete_cc(ctx, character, condition, self.bot)
            await ctx.respond(f"{condition} on {character} deleted.", ephemeral=True)
        elif mode == 'edit':
            result = await edit_cc(ctx, character, condition, new_value, self.bot)
            await ctx.respond(f"{condition} on {character} updated.", ephemeral=True)
        else:
            await ctx.respond("Failed", ephemeral=True)

        if not result:
            await ctx.respond("Failed", ephemeral=True)

    @i.command(description = "Show Custom Counters")
    async def cc_show(self, ctx: discord.ApplicationContext, character: str):
        #TODO - Make this GM only for NPCs
        await ctx.response.defer()
        cc_list = get_cc(ctx, character)
        output_string = f'{character}:\n'
        for row in cc_list:
            counter_string = f'{row[3]}: {row[4]}'
            output_string += counter_string
        await ctx.send_followup(output_string, ephemeral=True)



def setup(bot):
    bot.add_cog(InitiativeCog(bot))
