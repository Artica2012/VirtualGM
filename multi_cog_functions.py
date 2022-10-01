# multi_cog_functions.py

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
import datetime

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

async def output_datetime(ctx: discord.ApplicationContext, engine, bot):
    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()

            time = datetime.datetime(year=guild.time_year, month=guild.time_month, day=guild.time_day,
                                     hour=guild.time_hour, minute=guild.time_minute, second=guild.time_second)
            output_string = time.strftime("%A %B %d, %Y: %I:%M:%S %p")
            print(output_string)
            return output_string

    except NoResultFound as e:
        await ctx.channel.send(
            "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
            "proper channel or run `/i admin setup` to setup the initiative tracker",
            delete_after=30)
        return ""
    except Exception as e:
        print(f'output_datetime: {e}')
        report = ErrorReport(ctx, "output_datetime", e, bot)
        await report.report()
        return ""

def check_timekeeper(ctx:discord.ApplicationContext, engine):
    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            return guild.timekeeping
    except Exception as e:
        return False