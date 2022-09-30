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


def output_datetime(ctx: discord.ApplicationContext, engine, bot):
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
        print(f'set_cc: {e}')
        report = ErrorReport(ctx, "output_datetime", e, bot)
        await report.report()
        return ""


def advance_time(ctx: discord.ApplicationContext, engine, bot, second: int = 0, minute: int = 0, hour: int = 0,
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


    except NoResultFound as e:
        await ctx.channel.send(
            "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
            "proper channel or run `/i admin setup` to setup the initiative tracker",
            delete_after=30)
        return ""
    except Exception as e:
        print(f'set_cc: {e}')
        report = ErrorReport(ctx, "advance_time", e, bot)
        await report.report()
        return ""


class TimekeeperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    timekeeper = SlashCommandGroup('time', 'Time Keeper')

    @timekeeper.command(description="Setup Timekeeping")
    @option('time', description="Seconds per round")
    async def setup(self, ctx: discord.ApplicationContext, time: int = 6):
        try:
            with Session(self.engine) as session:
                guild = session.execute(select(Global).filter(
                    or_(
                        Global.tracker_channel == ctx.channel.id,
                        Global.gm_tracker_channel == ctx.channel.id
                    )
                )
                ).scalar_one()
                guild.timekeeping = True
                guild.time = time
                guild.time_second = 0
                guild.time_minute = 0
                guild.time_hour = 6
                guild.time_day = 1
                guild.time_month = 1
                guild.time_year = 4802
                session.commit()

            await ctx.respond("Timekeeper Setup Complete")
        except NoResultFound as e:
            await ctx.respond(
                "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                "proper channel or run `/i admin setup` to setup the initiative tracker",
                ephemeral=True)
            return False
        except Exception as e:
            print(f'set_cc: {e}')
            report = ErrorReport(ctx, "/time setup", e, self.bot)
            await report.report()
            await ctx.respond("Setup Failed")



def setup(bot):
    bot.add_cog(TimekeeperCog(bot))
