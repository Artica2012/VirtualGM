# pf2_functions.py


import os

# imports
import discord
import asyncio
import sqlalchemy as db
from discord import option
from discord.commands import SlashCommandGroup, option
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from database_models import Global, Base, TrackerTable, ConditionTable, MacroTable, get_tracker_table, \
    get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time
from PF2e.pathbuilder_importer import pathbuilder_import

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

PF2_attributes = ['AC','Fort', 'Reflex', 'Will', 'DC']

class PF2AddCharacterModal(discord.ui.Modal):
    def __init__(self, name:str, hp:int, init:str, initiative, player, ctx, emp, con, engine, *args, **kwargs ):
        self.name = name
        self.hp = hp
        self.init = init
        self.initiative = initiative
        self.player = player
        self.ctx = ctx
        self.emp = emp
        self.con = con
        self.engine = engine
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

            char_dicts =[{
                    'character_id':id_data[0][0],
                    'title': 'AC',
                    'number': int(self.children[0].value),
                },
                {
                    'character_id': id_data[0][0],
                    'title': 'Fort',
                    'number': int(self.children[1].value),
                },
                {
                    'character_id': id_data[0][0],
                    'title': 'Reflex',
                    'number': int(self.children[2].value),
                },
                {
                    'character_id': id_data[0][0],
                    'title': 'Will',
                    'number': int(self.children[3].value),
                },
                {
                    'character_id': id_data[0][0],
                    'title': 'DC',
                    'number': int(self.children[4].value),
                },
            ]

            con_stmt = self.con.insert().values(
                char_dicts
            )
            await conn.execute(con_stmt)

        await interaction.response.send_message(embeds=[embed])
