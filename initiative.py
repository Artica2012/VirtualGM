# initiative.py
# Initiative Tracker Module

# imports
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from discord import option

import sqlalchemy as db
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from database_models import Global, Base
from sqlalchemy.orm import Session, Query
from sqlalchemy import select, update, delete, insert

from dice_roller import DiceRoller

import os
from dotenv import load_dotenv

# define global variables
role_ids = [1011880400513151058, 1011880477298278461, 1011880538199556176]
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')

#################################################################
#################################################################
# FUNCTIONS

# Tables - These will allow a central place for changes, also saves a ton of lines of code

# The tracker table
def tracker_table(server: discord.Guild, metadata):
    tablename = f"Tracker_{server.id}"
    emp = db.Table(tablename, metadata,
                   db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                   db.Column('name', db.String(255), nullable=False, unique=True),
                   db.Column('init', db.INTEGER(), default=0),
                   db.Column('player', db.BOOLEAN, default=False),
                   db.Column('user', db.INTEGER(), nullable=False),
                   db.Column('current_hp', db.INTEGER(), default=0),
                   db.Column('max_hp', db.INTEGER(), default=1),
                   db.Column('temp_hp', db.INTEGER(), default=0),
                   )
    return emp


# The condition table
def condition_table(server: discord.Guild, metadata):
    tablename = f"Condition_{server.id}"
    con = db.Table(tablename, metadata,
                   db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                   db.Column('character_id', db.INTEGER(), ForeignKey(f'Tracker_{server.id}.id')),
                   db.Column('condition', db.String(255), nullable=False),
                   db.Column('duration', db.INTEGER()),
                   db.Column('beginning', db.BOOLEAN, default=False)
                   )
    return con


# Set up the tracker if it does not exit.db
def setup_tracker(server: discord.Guild, user: discord.User):
    try:
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        # engine = create_engine('postgresql://')
        conn = engine.connect()
        metadata = db.MetaData()
        emp = tracker_table(server, metadata)
        con = condition_table(server, metadata)
        metadata.create_all(engine)
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            guild = Global(
                guild_id=server.id,
                time=0,
                gm=user.id
            )
            session.add(guild)
            session.commit()

        return True
    except Exception as e:
        print(e)
        return False

def set_gm(server: discord.Guild, new_gm: discord.User):
    try:
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        # engine = create_engine('postgresql://')
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
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    metadata = db.MetaData()
    try:
        emp = tracker_table(server, metadata)
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
            conn.commit()
        return True
    except Exception as e:
        print(e)
        return False


# Add an NPC to the database
def add_npc(name: str, user: int, server: discord.Guild, HP: int):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    metadata = db.MetaData()
    try:
        emp = tracker_table(server, metadata)
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
            conn.commit()
        return True
    except Exception as e:
        print(e)
        return False

def delete_character(server: discord.Guild, name: str):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    metadata = db.MetaData()
    try:
        emp = tracker_table(server,metadata)
        stmt = delete(emp).where(emp.c.name == name)
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
        return True
    except Exception as e:
        print(e)
        return False



# Set the initiative
def set_init(server: discord.Guild, name: str, init: int):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    metadata = db.MetaData()
    try:
        emp = tracker_table(server, metadata)
        stmt = update(emp).where(emp.c.name == name).values(
            init=init
        )
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
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
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    with Session(engine) as session:
        # get current position in the initiative
        guild = session.execute(select(Global).filter_by(guild_id=server.id)).scalar_one()
        init_pos = int(guild.initiative)
        current_character = guild.saved_order
        # make sure that the current character is at the same place in initiative as it was before

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

    display_string = display_init(get_init_list(server), init_pos)
    return display_string


def get_init_list(server: discord.Guild):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    metadata = db.MetaData()
    emp = tracker_table(server, metadata)
    stmt = emp.select().order_by(emp.c.init.desc())
    # print(stmt)
    data = []
    with engine.connect() as conn:
        for row in conn.execute(stmt):
            print(row)
            data.append(row)
        # print(data)
        return data


def parse_init_list(server: discord.Guild, init_list: list):
    parsed_list = []
    for row in init_list:
        parsed_list.append(row[1])
    return parsed_list


def display_init(init_list: list, selected: int):
    row_data = []
    for row in init_list:
        row_data.append({'id': row[0],
                         'name': row[1],
                         'init': row[2],
                         'player': row[3],
                         'user': row[4],
                         'chp': row[5],
                         'maxhp': row[6],
                         'thp': row[7]
                         })

    output_string = "```" \
                    "Initiative:\n"
    for x, row in enumerate(row_data):
        if x == selected:
            selector = '>>>'
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
    output_string += '```'
    # print(output_string)
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
    else:
        hp_string = 'Critical'

    return hp_string

def heal(server: discord.Guild, name: str, ammount: int):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    metadata = db.MetaData()
    try:
        emp = tracker_table(server, metadata)
        stmt = emp.select().where(emp.c.name == name)
        compiled = stmt.compile()
        with engine.connect() as conn:
            data = []
            for row in conn.execute(stmt):
                data.append(row)

        chp = data[0][5]
        maxhp = data[0][6]
        new_hp = chp+ammount
        if new_hp > maxhp:
            new_hp = maxhp

        stmt = update(emp).where(emp.c.name == name).values(
            current_hp=new_hp
        )
        compiled = stmt.compile()
        with engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                return False
        return True
    except Exception as e:
        print(e)
        return False


#############################################################################
#############################################################################
# SLASH COMMANDS
# The Initiative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    initiative = SlashCommandGroup("initiative", "Initiative Tracker")

    @initiative.command(guild_ids=[GUILD])
    @discord.default_permissions(manage_messages=True)
    async def setup(self, ctx: discord.ApplicationContext):
        response = setup_tracker(ctx.guild, ctx.user)
        if response:
            await ctx.respond("Server Setup", ephemeral=True)
        else:
            await ctx.respond("Server Failed", ephemeral=True)

    @initiative.command(guild_ids=[GUILD])
    @discord.default_permissions(manage_messages=True)
    async def transfer_gm(self, ctx: discord.ApplicationContext, new_gm: discord.User):
        response = set_gm(ctx.guild, new_gm)
        if response:
            await ctx.respond(f"GM Permissions trasferred to {new_gm.mention}")
        else:
            await ctx.respond("Permission Transfer Failed", ephemeral=True)

    @initiative.command(guild_ids=[GUILD])
    async def add_character(self, ctx: discord.ApplicationContext, name: str, hp: int):
        response = add_player(name, ctx.user.id, ctx.guild, hp)
        if response:
            await ctx.respond(f"Character {name} added successfully", ephemeral=True)
        else:
            await ctx.respond(f"Error Adding Character", ephemeral=True)

    @initiative.command(guild_ids=[GUILD])
    async def add_npc(self, ctx: discord.ApplicationContext, name: str, hp: int):
        response = add_npc(name, ctx.user.id, ctx.guild, hp)
        if response:
            await ctx.respond(f"Character {name} added successfully", ephemeral=True)
        else:
            await ctx.respond(f"Error Adding Character", ephemeral=True)

    @initiative.command(guild_ids=[GUILD])
    @discord.default_permissions(manage_messages=True)
    async def start_initiative(self, ctx: discord.ApplicationContext):
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        init_list = get_init_list(ctx.guild)

        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild_id)).scalar_one()
            if guild.gm != ctx.user.id:
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            guild.initiative = 0
            guild.saved_order = parse_init_list(ctx.guild, init_list)[0]
            session.commit()
        display_string = display_init(init_list, 0)
        await ctx.respond(display_string)

    @initiative.command(guild_ids=[GUILD])
    async def end_initiative(self, ctx: discord.ApplicationContext):
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild_id)).scalar_one()
            if guild.gm != ctx.user.id:
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            guild.initiative = None
            guild.saved_order = None
            session.commit()
        await ctx.respond("Initiative Ended.")

    @initiative.command(guild_ids=[GUILD])
    async def next(self, ctx: discord.ApplicationContext):
        display_string = advance_initiative(ctx.guild)
        await ctx.respond(display_string)

    @initiative.command(guild_ids=[GUILD])
    async def init(self, ctx: discord.ApplicationContext, character: str, init: str):
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild.id)).scalar_one()
            if character == guild.saved_order:
                await ctx.respond(f"Please wait until {character} is not the active character in initiative before "
                                  f"resetting its initiative.", ephemeral=True)
            else:
                dice = DiceRoller('')
                try:
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

    @initiative.command(guild_ids=[GUILD])
    @discord.default_permissions(manage_messages=True)
    async def delete_character(self, ctx: discord.ApplicationContext, character: str):
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild.id)).scalar_one()
            if guild.gm != ctx.user.id:
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            if character == guild.saved_order:
                await ctx.respond(f"Please wait until {character} is not the active character in initiative before "
                                  f"deleting it.", ephemeral=True)
            else:
                delete_character(ctx.guild, character)
                await ctx.respond(f'{character} deleted', ephemeral=True)


#TODO Finish this
    @initiative.command(guild_ids=[GUILD])
    @option('name', description="Character Name")
    @option('mode', choices=['Damage', 'Heal'])
    async def heal_harm(self, ctx: discord.ApplicationContext, name: str, mode: str, ammount: int):
        response = heal(ctx.guild, name, ammount)
        await ctx.respond("Healed")

def setup(bot):
    bot.add_cog(InitiativeCog(bot))
