# initiative.py
# Initiative Tracker Module

#imports
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
import database_operations
import sqlite3
import sqlalchemy as db

import os
from dotenv import load_dotenv

# define global variables
role_ids = [1011880400513151058, 1011880477298278461, 1011880538199556176]
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')

# Functions

# Set up the tracker if it does not exit.
def setup_tracker(server: discord.Guild):
    engine = db.create_engine(f'sqlite:///{SERVER_DATA}.db')
    conn = engine.connect()
    metadata = db.MetaData()
    ID = server.id
    emp = db.Table(ID, metadata,
                   db.Column('ID', db.INTEGER(), autoincrement=True, primary_key=True),
                   db.Column('name', db.String(255), nullable=False),
                   db.Column('init', db.INTEGER(), default=0),
                   db.Column('player', db.BOOLEAN, default=False),
                   db.Column('user', db.INTEGER(), nullable=False)
                   )
    metadata.create_all(engine)
    return emp

# Add a player to the database
def add_player(name: str, user: int, server: discord.Guild):
    engine = db.create_engine(f'sqlite:///{SERVER_DATA}.db')
    ID = server.id
    metadata = db.MetaData()
    emp = db.Table(ID, metadata,
                   db.Column('ID', db.INTEGER(), autoincrement=True, primary_key=True),
                   db.Column('name', db.String(255), nullable=False),
                   db.Column('init', db.INTEGER(), default=0),
                   db.Column('player', db.BOOLEAN, default=False),
                   db.Column('user', db.INTEGER(), nullable=False)
                   )
    ins = emp.insert().values(name=name, player=True, user=user)
    print(str(ins))
    with engine.connect() as conn:
        result = conn.execute(ins)

# Add an NPC to the database
def add_npc(name: str, user: int, server: discord.Guild):
    engine = db.create_engine(f'sqlite:///{SERVER_DATA}.db')
    ID = server.id
    metadata = db.MetaData()
    emp = db.Table(ID, metadata,
                   db.Column('ID', db.INTEGER(), autoincrement=True, primary_key=True),
                   db.Column('name', db.String(255), nullable=False),
                   db.Column('init', db.INTEGER(), default=0),
                   db.Column('player', db.BOOLEAN, default=False),
                   db.Column('user', db.INTEGER(), nullable=False)
                   )
    ins = emp.insert().values(name=name, player=False, user=user)
    print(str(ins))
    with engine.connect() as conn:
        result = conn.execute(ins)

# The Iniative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    initiative = SlashCommandGroup("initiative", "Initiative Tracker")

    @initiative.command(guild_ids=[GUILD])
    async def setup(self, ctx: discord.ApplicationContext):
        emp = setup_tracker(ctx.guild)
        await ctx.respond("Server Setup", ephemeral=True)

    @initiative.command(guild_ids=[GUILD])
    async def add_character(self, ctx: discord.ApplicationContext, name: str):
        try:
            add_player(name, ctx.user.id, ctx.guild)
            await ctx.respond(f"Character {name} added successfully", ephemeral=True)
        except Exception as e:
            print(e)
            await ctx.respond(f"Error Adding Character: Exception:{e}", ephemeral=True)


def setup(bot):
    bot.add_cog(InitiativeCog(bot))
