# initiative.py
# Initiative Tracker Module

# imports
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from sqlalchemy import insert
import database_models
import database_operations
import sqlite3
import sqlalchemy as db
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from database_models import Global, ConditionTable, TrackerTable, Base
from sqlalchemy.orm import Session, Query
from sqlalchemy import select

import os
from dotenv import load_dotenv

# define global variables
role_ids = [1011880400513151058, 1011880477298278461, 1011880538199556176]
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')

'''
Database Schema

Table: Tracker
id | name | init | player | user

Table: GuildID_conditions
id | character_id | condition | duration | beginning

Table: global_manager
id | time | initiative

'''


# Function

#TODO - FINISH THIS
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


# Set up the tracker if it does not exit.db
def setup_tracker(server: discord.Guild):
    try:
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        # engine = create_engine('postgresql://')
        conn = engine.connect()
        metadata = db.MetaData()
        ID = server.id
        emp = db.Table(f"Tracker_{ID}", metadata,
                       db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                       db.Column('name', db.String(255), nullable=False, unique=True),
                       db.Column('init', db.INTEGER(), default=0),
                       db.Column('player', db.BOOLEAN, default=False),
                       db.Column('user', db.INTEGER(), nullable=False),
                       db.Column('current_hp', db.INTEGER(), default=0),
                       db.Column('max_hp', db.INTEGER(), default=1),
                       db.Column('temp_hp', db.INTEGER(), default=0),
                       )
        con = db.Table(f"Condition_{ID}", metadata,
                       db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                       db.Column('character_id', db.INTEGER(), ForeignKey(f'Tracker_{ID}.id')),
                       db.Column('condition', db.String(255), nullable=False),
                       db.Column('duration', db.INTEGER()),
                       db.Column('beginning', db.BOOLEAN, default=False)
                       )
        metadata.create_all(engine)
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            guild = Global(
                guild_id=server.id,
                time=0,
            )
            session.add(guild)
            session.commit()

        return True
    except Exception as e:
        print(e)
        return False


# Add a player to the database
def add_player(name: str, user: int, server: discord.Guild, HP: int):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    tablename = f'Tracker_{server.id}'
    metadata = db.MetaData()
    try:
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
    tablename = f'Tracker_{server.id}'
    metadata = db.MetaData()
    try:
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

def advance_initiative(server: discord.Guild):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    with Session(engine) as session:
        guild = session.execute(select(Global).filter_by(guild_id=server.id)).scalar_one()




def get_init_list(server: discord.Guild):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    tablename = f'Tracker_{server.id}'
    metadata = db.MetaData()
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
    # TODO - Order this by descending init
    stmt = emp.select()
    print(stmt)
    with engine.connect() as conn:
        for row in conn.execute(stmt):
            print(row)
        return conn.execute(stmt)

    # with Session(engine) as session:
    #     results = session.execute(f"SELECT * FROM Tracker WHERE guild = {server.id} ORDER BY init")
    #     for character in results:
    #         print(character)


# The Initiative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    initiative = SlashCommandGroup("initiative", "Initiative Tracker")

    @initiative.command(guild_ids=[GUILD])
    async def setup(self, ctx: discord.ApplicationContext):
        response = setup_tracker(ctx.guild)
        if response:
            await ctx.respond("Server Setup", ephemeral=True)
        else:
            await ctx.respond("Server Failed", ephemeral=True)

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
    async def start_initiative(self, ctx: discord.ApplicationContext):
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        with Session(engine) as session:
            guild = session.execute(select(Global).filter_by(guild_id=ctx.guild_id)).scalar_one()
            guild.initiative = 100
            session.commit()
        get_init_list(ctx.guild)



def setup(bot):
    bot.add_cog(InitiativeCog(bot))
