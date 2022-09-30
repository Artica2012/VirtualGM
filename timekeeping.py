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
from initiative import update_pinned_tracker

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


async def set_datetime(ctx: discord.ApplicationContext, engine, bot, second: int, minute: int, hour: int, day: int,
                       month: int, year: int, time: int = None):
    try:
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.channel.id,
                    Global.gm_tracker_channel == ctx.channel.id
                )
            )
            ).scalar_one()
            guild.timekeeping = True
            if time:
                # print(time)
                guild.time = time
            if second != None:
                # print(second)
                guild.time_second = second
            if minute != None:
                # print(minute)
                guild.time_minute = minute
            if hour != None:
                # print(hour)
                guild.time_hour = hour
            if day != None:
                # print(day)
                guild.time_day = day
            if month != None:
                # print(month)
                guild.time_month = month
            if year != None:
                # print(year)
                guild.time_year = year
            session.commit()

            #update the tracker
            await update_pinned_tracker(ctx, engine, bot)

            return True
    except NoResultFound as e:
        await ctx.channel.send(
            "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
            "proper channel or run `/i admin setup` to setup the initiative tracker",
            delete_after=30)
        return False
    except Exception as e:
        print(f'set_datetime: {e}')
        report = ErrorReport(ctx, "set_datetime", e, bot)
        await report.report()
        return False


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


async def advance_time(ctx: discord.ApplicationContext, engine, bot, second: int = 0, minute: int = 0, hour: int = 0,
                       day: int = 0):
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
            new_time = time + datetime.timedelta(seconds=second, minutes=minute, hours=hour, days=day)
            guild.time_second = new_time.second
            guild.time_minute = new_time.minute
            guild.time_hour = new_time.hour
            guild.time_day = new_time.day
            guild.time_month = new_time.month
            guild.time_year = new_time.year
            session.commit()

            # update tracker
            await update_pinned_tracker(ctx, engine, bot)
            return True

    except NoResultFound as e:
        await ctx.channel.send(
            "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
            "proper channel or run `/i admin setup` to setup the initiative tracker",
            delete_after=30)
        return False
    except Exception as e:
        print(f'advance_time: {e}')
        report = ErrorReport(ctx, "advance_time", e, bot)
        await report.report()
        return False


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
                                        year=4802, time=time)
            if result:
                await ctx.respond("Timekeeper Setup Complete", ephemeral=True)
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
                       month: int = None, year: int = None):
        try:
            result = await set_datetime(ctx, self.engine, self.bot, minute=minute, hour=hour, day=day, month=month,
                                        year=year)
            if result:
                await ctx.respond("Date and Time Set", ephemeral=True)
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
    async def advance(self, ctx: discord.ApplicationContext, amount:int, unit:str="minute"):
        if unit == "minute":
            result = await advance_time(ctx, self.engine, self.bot, minute=amount)
            #TODO - FINISH THIS


def setup(bot):
    bot.add_cog(TimekeeperCog(bot))
