# initiative.py
# Initiative Tracker Module

# imports
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
import database_operations
import sqlite3
import sqlalchemy as db
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from database_models import Global, ConditionTable, TrackerTable, Base
from sqlalchemy.orm import Session,Query
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

# Set up the tracker if it does not exit.
def setup_tracker(server: discord.Guild):
    try:
        engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            guild = Global(
                guild_id = server.id,
                time = 0,
            )
            session.add(guild)
            session.commit()


        return True
    except Exception as e:
        print(e)
        return False


# Add a player to the database
def add_player(name: str, user: int, server: discord.Guild):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    try:
        with Session(engine) as session:
            character = TrackerTable(
                name = name,
                init = 0,
                player = True,
                user = user,
                guild = server.id

            )
            session.add(character)
            session.commit()
            return True
    except Exception as e:
        return False

# Add an NPC to the database
def add_npc(name: str, user: int, server: discord.Guild):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    try:
        with Session(engine) as session:
            character = TrackerTable(
                name=name,
                init=0,
                player=False,
                user=user,
                guild=server.id
            )
            session.add(character)
            session.commit()
            return True
    except Exception as e:
        return False


def advance_initiative(server: discord.Guild):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    with Session(engine) as session:
        guild = session.execute(select(Global).filter_by(guild_id=server.id)).scalar_one()

def get_init_list(server: discord.Guild):
    engine = create_engine(f'sqlite:///{SERVER_DATA}.db', future=True)
    with Session(engine) as session:
        results = session.execute(f"SELECT * FROM Tracker WHERE guild = {server.id} ORDER BY init")
        for character in results:
            print(character)


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
    async def add_character(self, ctx: discord.ApplicationContext, name: str):
        response = add_player(name, ctx.user.id, ctx.guild)
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
