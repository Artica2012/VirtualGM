# d4e_cog.py
# For slash commands specific to oathfinder 2e
# system specific module

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

import D4e.d4e_functions
from database_models import Global, Base, TrackerTable, ConditionTable, MacroTable, get_tracker_table, \
    get_condition_table, get_macro_table, get_condition, get_macro, get_tracker
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time
from PF2e.pathbuilder_importer import pathbuilder_import
from initiative import update_pinned_tracker

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

# ---------------------------------------------------------------
# ---------------------------------------------------------------
# UTILITY FUNCTIONS

# Checks to see if the user of the slash command is the GM, returns a boolean
async def gm_check(ctx, engine):
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
        if int(guild.gm) != int(ctx.interaction.user.id):
            return False
        else:
            return True

class D4eCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

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
                    char_result = await session.execute(
                        select(Tracker).where(Tracker.user == ctx.interaction.user.id))
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

    async def cc_select_visible(self, ctx: discord.AutocompleteContext):
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
                con_result = await session.execute(select(Condition)
                    .where(Condition.character_id == char.id)
                    .where(Condition.visible == True))
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


    async def a_macro_select(self, ctx: discord.AutocompleteContext):
        character = ctx.options['character']
        Tracker = await get_tracker(ctx, self.engine)
        Macro = await get_macro(ctx, self.engine)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        try:
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(
                    Tracker.name == character
                ))
                char = char_result.scalars().one()
            async with async_session() as session:
                macro_result = await session.execute(
                    select(Macro).where(Macro.character_id == char.id).order_by(Macro.name.asc()))
                macro_list = macro_result.scalars().all()
            macros = []
            for row in macro_list:
                await asyncio.sleep(0)
                if not ',' in row.macro:
                    macros.append(f"{row.name}: {row.macro}")

            await self.engine.dispose()
            return macros
        except Exception as e:
            print(f'a_macro_select: {e}')
            report = ErrorReport(ctx, self.a_macro_select.__name__, e, self.bot)
            await report.report()
            return False
    dd = SlashCommandGroup('d4e', "D&D 4th Edition Specific Commands")

    @dd.command(description="D&D 4e auto save")
    # @commands.slash_command(name="d4e_save", guild_ids=[GUILD])
    @option('character', description='Character Attacking', autocomplete=character_select_gm)
    @option('condition', description="Select Condition", autocomplete=cc_select_visible)
    async def save(self, ctx:discord.ApplicationContext, character:str, condition:str, modifier:str=''):
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



def setup(bot):
    bot.add_cog(D4eCog(bot))
