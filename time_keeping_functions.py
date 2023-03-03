# time_keeping_functions.py

import datetime
import logging
import os
from typing import Optional

# imports
import discord
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from database_models import Global
from error_handling_reporting import ErrorReport

# define global variables

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")


async def get_time(ctx: discord.ApplicationContext, engine, guild=None):
    if ctx is None and guild is None:
        raise LookupError("No guild reference")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            if ctx is None:
                result = await session.execute(select(Global).where(Global.id == guild.id))
            else:
                result = await session.execute(
                    select(Global).where(
                        or_(
                            Global.tracker_channel == ctx.interaction.channel_id,
                            Global.gm_tracker_channel == ctx.interaction.channel_id,
                        )
                    )
                )
            guild = result.scalars().one()

            time = datetime.datetime(
                year=guild.time_year,
                month=guild.time_month,
                day=guild.time_day,
                hour=guild.time_hour,
                minute=guild.time_minute,
                second=guild.time_second,
            )
        await engine.dispose()
        return time

    except NoResultFound:
        if ctx is not None:
            await ctx.channel.send(
                (
                    "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                    "proper channel or run `/i admin setup` to setup the initiative tracker"
                ),
                delete_after=30,
            )
        return None
    except Exception as e:
        logging.warning(f"get_time: {e}")
        return None


async def output_datetime(ctx: discord.ApplicationContext, engine, bot, guild=None):
    if ctx is None and guild is None:
        raise LookupError("No guild reference")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            if ctx is None:
                result = await session.execute(select(Global).where(Global.id == guild.id))
            else:
                result = await session.execute(
                    select(Global).where(
                        or_(
                            Global.tracker_channel == ctx.interaction.channel_id,
                            Global.gm_tracker_channel == ctx.interaction.channel_id,
                        )
                    )
                )
            guild = result.scalars().one()

            time = datetime.datetime(
                year=guild.time_year,
                month=guild.time_month,
                day=guild.time_day,
                hour=guild.time_hour,
                minute=guild.time_minute,
                second=guild.time_second,
            )
            output_string = time.strftime("Month: %m Day: %d, Year: %y: %I:%M:%S %p")
            # print(output_string)
        await engine.dispose()
        return output_string

    except NoResultFound:
        if ctx is not None:
            await ctx.channel.send(
                (
                    "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                    "proper channel or run `/i admin setup` to setup the initiative tracker"
                ),
                delete_after=30,
            )
        return ""
    except Exception as e:
        logging.error(f"output_datetime: {e}")
        if ctx is not None and bot is not None:
            report = ErrorReport(ctx, "output_datetime", e, bot)
            await report.report()
        return ""


async def check_timekeeper(ctx, engine, guild=None):
    if ctx is None and guild is None:
        raise LookupError("No guild reference")

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            if ctx is None:
                result = await session.execute(select(Global).where(Global.id == guild.id))
            else:
                result = await session.execute(
                    select(Global).where(
                        or_(
                            Global.tracker_channel == ctx.interaction.channel_id,
                            Global.gm_tracker_channel == ctx.interaction.channel_id,
                        )
                    )
                )
            guild = result.scalars().one()
        await engine.dispose()
        return guild.timekeeping
    except Exception:
        return False


async def set_datetime(
    ctx: discord.ApplicationContext,
    engine,
    bot,
    second: Optional[int],
    minute: Optional[int],
    hour: Optional[int],
    day: Optional[int],
    month: Optional[int],
    year: Optional[int],
    time: Optional[int] = None,
):
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(
                select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id,
                    )
                )
            )
            guild = result.scalars().one()
            guild.timekeeping = True
            if time is not None:
                # print(time)
                guild.time = time
            if second is not None:
                # print(second)
                guild.time_second = second
            if minute is not None:
                # print(minute)
                guild.time_minute = minute
            if hour is not None:
                # print(hour)
                guild.time_hour = hour
            if day is not None:
                # print(day)
                guild.time_day = day
            if month is not None:
                # print(month)
                guild.time_month = month
            if year is not None:
                # print(year)
                guild.time_year = year
            await session.commit()
            await engine.dispose()
        return True
    except NoResultFound:
        await ctx.channel.send(
            (
                "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                "proper channel or run `/i admin setup` to setup the initiative tracker"
            ),
            delete_after=30,
        )
        return False
    except Exception as e:
        print(f"set_datetime: {e}")
        report = ErrorReport(ctx, "set_datetime", e, bot)
        await report.report()
        return False


async def advance_time(
    ctx: discord.ApplicationContext,
    engine,
    bot,
    second: int = 0,
    minute: int = 0,
    hour: int = 0,
    day: int = 0,
    guild=None,
):
    if ctx is None and guild is None:
        raise LookupError("No guild reference")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            if ctx is None:
                result = await session.execute(select(Global).where(Global.id == guild.id))
            else:
                result = await session.execute(
                    select(Global).where(
                        or_(
                            Global.tracker_channel == ctx.interaction.channel_id,
                            Global.gm_tracker_channel == ctx.interaction.channel_id,
                        )
                    )
                )
            guild = result.scalars().one()

            time = datetime.datetime(
                year=guild.time_year,
                month=guild.time_month,
                day=guild.time_day,
                hour=guild.time_hour,
                minute=guild.time_minute,
                second=guild.time_second,
            )
            new_time = time + datetime.timedelta(seconds=second, minutes=minute, hours=hour, days=day)
            guild.time_second = new_time.second
            guild.time_minute = new_time.minute
            guild.time_hour = new_time.hour
            guild.time_day = new_time.day
            guild.time_month = new_time.month
            guild.time_year = new_time.year
            await session.commit()

        await engine.dispose()
        return True

    except NoResultFound:
        if ctx is not None:
            await ctx.channel.send(
                (
                    "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                    "proper channel or run `/i admin setup` to setup the initiative tracker"
                ),
                delete_after=30,
            )
        return False
    except Exception as e:
        logging.error(f"advance_time: {e}")
        return False


async def time_left(ctx: discord.ApplicationContext, engine, bot, con_time):
    time_stamp = datetime.datetime.fromtimestamp(con_time)
    current_time = await get_time(ctx, engine)
    time_left = time_stamp - current_time
    days_left = time_left.days
    processed_minutes_left = divmod(time_left.seconds, 60)[0]
    processed_seconds_left = divmod(time_left.seconds, 60)[1]
    if processed_seconds_left < 10:
        processed_seconds_left = f"0{processed_seconds_left}"
    if days_left != 0:
        con_string = f"{days_left} Days, {processed_minutes_left}:{processed_seconds_left}"
    else:
        con_string = f"{processed_minutes_left}:{processed_seconds_left}"
    return con_string
