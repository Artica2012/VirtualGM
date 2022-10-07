# timekeeping.py

# imports
import datetime
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
from initiative import update_pinned_tracker, check_cc
from time_keeping_functions import output_datetime, check_timekeeper, set_datetime, advance_time

import os
from dotenv import load_dotenv
import database_operations

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


# Timekeeper Cog - For managing the time functions
class TimekeeperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    timekeeper = SlashCommandGroup('time', 'Time Keeper')

    # The timekeeper setup functionality
    @timekeeper.command(description="Setup Timekeeping")
    @option('time', description="Seconds per round")
    async def setup(self, ctx: discord.ApplicationContext, time: int = 6):
        try:
            result = await set_datetime(ctx, self.engine, self.bot, second=0, minute=0, hour=6, day=1, month=1,
                                        year=2001, time=time)
            if result:
                await ctx.respond("Timekeeper Setup Complete", ephemeral=True)
                await update_pinned_tracker(ctx, self.engine, self.bot)
                # await output_datetime(ctx, self.engine, self.bot)
            else:
                await ctx.respond("Error Setting Up Timekeeper", ephemeral=True)
        except NoResultFound as e:
            await ctx.respond(
                "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                "proper channel or run `/i admin setup` to setup the initiative tracker",
                ephemeral=True)
        except Exception as e:
            print(f'setup: {e}')
            report = ErrorReport(ctx, "/time setup", e, self.bot)
            await report.report()
            await ctx.respond("Setup Failed")

    @timekeeper.command(description="Set Date/Time")
    async def set_time(self, ctx: discord.ApplicationContext, minute: int = None, hour: int = None, day: int = None,
                       month: int = None):
        try:
            result = await set_datetime(ctx, self.engine, self.bot, second=0, minute=minute, hour=hour, day=day,
                                        month=month, year=None)
            if result:
                await ctx.respond("Date and Time Set", ephemeral=True)
                await check_cc(ctx, self.engine, self.bot)
                await update_pinned_tracker(ctx, self.engine, self.bot)
            else:
                await ctx.respond("Error Setting Date and Time", ephemeral=True)
        except NoResultFound as e:
            await ctx.respond(
                "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                "proper channel or run `/i admin setup` to setup the initiative tracker",
                ephemeral=True)
        except Exception as e:
            print(f'set_time: {e}')
            report = ErrorReport(ctx, "/set_time", e, self.bot)
            await report.report()
            await ctx.respond("Setup Failed")

    @timekeeper.command(description="Advance Time")
    @option('amount', description="Amount to advance")
    @option('unit', choices=['minute', 'hour', 'day'])
    async def advance(self, ctx: discord.ApplicationContext, amount: int, unit: str = "minute"):
        if unit == "minute":
            result = await advance_time(ctx, self.engine, self.bot, minute=amount)
        elif unit == "hour":
            result = await advance_time(ctx, self.engine, self.bot, hour=amount)
        elif unit == "day":
            result = await advance_time(ctx, self.engine, self.bot, day=amount)
        else:
            result = False

        if result:
            await ctx.respond(
                f"Time advanced to by {amount} {unit}(s). New time is: {await output_datetime(ctx, self.engine, self.bot)}")
            await check_cc(ctx, self.engine, self.bot)
            await update_pinned_tracker(ctx, self.engine, self.bot)
        else:
            await ctx.respond("Failed to advance time.")


def setup(bot):
    bot.add_cog(TimekeeperCog(bot))
