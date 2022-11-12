# auto_complete.py

# Consolidating all of the autocompletes into one place.

# imports
import asyncio
import os
import logging
import sys
import datetime
import inspect

import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import or_, not_
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import Global, get_macro, get_tracker, get_condition
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
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


async def gm_check(ctx, engine):
    # bughunt code
    logging.info(f"{datetime.datetime.now()} - attack_cog gm_check")

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


async def character_select(self, ctx: discord.AutocompleteContext):
    logging.info(f"{datetime.datetime.now()} - character_select")
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker.name))
            character = char_result.scalars().all()
        return character
    except NoResultFound as e:
        return []
    except Exception as e:
        print(f'character_select: {e}')
        report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
        await report.report()
        return []


async def character_select_gm(self, ctx: discord.AutocompleteContext):
    # bughunt code
    logging.info(f"{datetime.datetime.now()} - attack_cog character_select_gm")
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    gm_status = await gm_check(ctx, engine)

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            if gm_status:
                char_result = await session.execute(select(Tracker.name))
            else:
                char_result = await session.execute(select(Tracker.name).where(Tracker.user == ctx.interaction.user.id))
            character = char_result.scalars().all()
            return character
    except NoResultFound as e:
        return []
    except Exception as e:
        print(f'character_select_gm: {e}')
        report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
        await report.report()
        return []

async def npc_select(self, ctx: discord.AutocompleteContext):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    character_list = []

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker.name).where(Tracker.player == False))
            character = char_result.scalars().all()
        return character
    except NoResultFound as e:
        return []
    except Exception as e:
        print(f'character_select: {e}')
        report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
        await report.report()
        return []


async def macro_select(self, ctx: discord.AutocompleteContext):
    character = ctx.options['character']
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    Tracker = await get_tracker(ctx, engine)
    Macro = await get_macro(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == character
            ))
            char = char_result.scalars().one()

        # async with async_session() as session:
        #     macro_result = await session.execute(
        #         select(Macro).where(Macro.character_id == char.id).order_by(Macro.name.asc()))
        #     macro_list = macro_result.scalars().all()

        async with async_session() as session:
            macro_result = await session.execute(
                select(Macro.name).where(Macro.character_id == char.id).order_by(Macro.name.asc()))
            macro_list = macro_result.scalars().all()
        #
        # macros = []
        # for row in macro_list:
        #     await asyncio.sleep(0)
        #     macros.append(f"{row.name}: {row.macro}")

        # await engine.dispose()
        return macro_list
    except Exception as e:
        print(f'a_macro_select: {e}')
        report = ErrorReport(ctx, self.macro_select.__name__, e, self.bot)
        await report.report()
        return False


async def a_macro_select(self, ctx: discord.AutocompleteContext):
    # bughunt code
    logging.info(f"{datetime.datetime.now()} - attack_cog a_macro_select")

    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    character = ctx.options['character']
    Tracker = await get_tracker(ctx, engine)
    Macro = await get_macro(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == character
            ))
            char = char_result.scalars().one()
        async with async_session() as session:
            macro_result = await session.execute(
                select(Macro.name)
                    .where(Macro.character_id == char.id)
                    .where(not_(Macro.macro.contains(',')))
                    .order_by(Macro.name.asc()))
            macro_list = macro_result.scalars().all()
        return macro_list
        # macros = []
        # for row in macro_list:
        #     await asyncio.sleep(0)
        #     if not ',' in row.macro:
        #         macros.append(f"{row.name}: {row.macro}")
        #
        # await engine.dispose()
        # return macros
    except NoResultFound as e:
        return []
    except Exception as e:
        print(f'a_macro_select: {e}')
        report = ErrorReport(ctx, self.a_macro_select.__name__, e, self.bot)
        await report.report()
        return False

async def cc_select(self, ctx: discord.AutocompleteContext):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    character = ctx.options['character']

    con_list = []
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == character
            ))
            char = char_result.scalars().one()
        async with async_session() as session:
            con_result = await session.execute(select(Condition.title).where(
                Condition.character_id == char.id
            ))
            condition = con_result.scalars().all()
        return condition
    except NoResultFound as e:
        return []
    except Exception as e:
        print(f'cc_select: {e}')
        report = ErrorReport(ctx, self.cc_select.__name__, e, self.bot)
        await report.report()
        return []
