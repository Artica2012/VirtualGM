# time_keeping_functions.py

import datetime
import os

# imports
import discord
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from database_models import Global
from error_handling_reporting import ErrorReport

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


async def get_time(ctx: discord.ApplicationContext, engine, bot):
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
            return time

    except NoResultFound as e:
        await ctx.channel.send(
            "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
            "proper channel or run `/i admin setup` to setup the initiative tracker",
            delete_after=30)
        return None
    except Exception as e:
        print(f'output_datetime: {e}')
        report = ErrorReport(ctx, "get_time", e, bot)
        await report.report()
        return None


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
            output_string = time.strftime("Month: %m Day: %d, Year: %y: %I:%M:%S %p")
            # print(output_string)
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


def check_timekeeper(ctx: discord.ApplicationContext, engine):
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
