import logging
import os

import discord
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from database_models import Global, get_tracker
from database_operations import get_asyncio_db_engine
from sqlalchemy import or_, select, false, true

from error_handling_reporting import ErrorReport

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    # TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    # TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")


async def get_guild(ctx, guild, refresh=False):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    if guild is not None and not refresh:
        return guild
    if ctx is None and guild is None:
        raise LookupError("No guild reference")

    async with async_session() as session:
        if ctx is None:
            logging.info("Refreshing Guild")
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
        return result.scalars().one()


async def gm_check(ctx, engine):
    logging.info("gm_check")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Global.gm).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id,
                    )
                )
            )
            gm = result.scalars().one()
            if int(gm) != int(ctx.interaction.user.id):
                return False
            else:
                return True
    except Exception:
        return False


async def player_check(ctx: discord.ApplicationContext, engine, bot, character: str):
    logging.info("player_check")
    try:
        Tracker = await get_tracker(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = char_result.scalars().one()
        return character

    except Exception as e:
        logging.warning(f"player_check: {e}")
        report = ErrorReport(ctx, player_check.__name__, e, bot)
        await report.report()
