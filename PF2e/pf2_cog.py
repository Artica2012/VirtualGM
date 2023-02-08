# pf2_cog.py
# For slash commands specific to oathfinder 2e
# system specific module
import logging
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

import auto_complete
from database_models import Global, Base, TrackerTable, ConditionTable, MacroTable, get_tracker_table, \
    get_condition_table, get_macro_table, get_tracker
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time
from PF2e.pathbuilder_importer import pathbuilder_import
from PF2e.NPC_importer import npc_lookup
from PF2e.pf2_functions import edit_stats
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

class PF2Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    pf2 = SlashCommandGroup('pf2', "Pathfinder 2nd Edition Specific Commands")

    @pf2.command(description="Pathbuilder Import")
    @option('pathbuilder_id', description="Pathbuilder Export ID", required=True)
    async def pb_import(self, ctx:discord.ApplicationContext, name:str, pathbuilder_id:int):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer(ephemeral=True)

        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )))
                guild = result.scalars().one()

                if guild.system == 'PF2':
                    response = await pathbuilder_import(ctx, engine, self.bot, name, str(pathbuilder_id))
                    if response:
                        await update_pinned_tracker(ctx, engine, self.bot)
                        await ctx.send_followup('Success')

                    else:
                        await ctx.send_followup('Import Failed')
                else:
                    await ctx.send_followup('System not assigned as Pathfinder 2e. Please ensure that the correct system '
                                      'was set at table setup')
        except Exception as e:
            await ctx.send_followup('Error')
            logging.info(f"pb_import: {e}")
            report = ErrorReport(ctx, "pb_import", e, self.bot)
            await report.report()



    @pf2.command(description="Pathbuilder Import")
    @option('elite_weak', choices=['weak', 'elite'], required=False)
    async def add_npc(self, ctx:discord.ApplicationContext, name:str, lookup:str, elite_weak:str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        await ctx.response.defer()
        response = await npc_lookup(ctx, engine, lookup_engine, self.bot, name, lookup, elite_weak)
        if not response:
            await ctx.send_followup('Import Failed')


    # @pf2.command(description="Edit PC or NPC Stats")
    # @option('name', description="Character Name", input_type=str, autocomplete=auto_complete.character_select_gm, )
    # async def edit(self, ctx: discord.ApplicationContext, name: str,):
    #     engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    #     response = False
    #
    #     response = await edit_stats(ctx, engine, self.bot, name)
    #     if not response:
    #         await ctx.respond(f"Error Editing Character", ephemeral=True)
    #     else:
    #         await update_pinned_tracker(ctx, engine, self.bot)



def setup(bot):
    bot.add_cog(PF2Cog(bot))
