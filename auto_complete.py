# auto_complete.py

# Consolidating all of the autocompletes into one place.

# imports
import os
import logging
import datetime

import discord
from dotenv import load_dotenv
from sqlalchemy import false, not_, select, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import PF2e.pf2_functions
from character_functions import get_character
import initiative
from database_models import get_macro, get_tracker, get_condition
from database_operations import get_asyncio_db_engine

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


async def hard_lock(ctx: discord.ApplicationContext, name: str):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    Tracker = await get_tracker(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker.user).where(Tracker.name == name))
            user = result.scalars().one()
            # print(user)
            # print(ctx.user.id)

        if await gm_check(ctx, engine) or ctx.interaction.user.id == user:
            return True
        else:
            return False
    except Exception:
        logging.error("hard_lock")
        return False


async def gm_check(ctx, engine):
    # bughunt code
    logging.info(f"{datetime.datetime.now()} - attack_cog gm_check")
    try:
        guild = await initiative.get_guild(ctx, None)
        if int(guild.gm) != int(ctx.interaction.user.id):
            return False
        else:
            return True
    except Exception:
        return False


# Autocompletes
# returns a list of all characters
async def character_select(ctx: discord.AutocompleteContext):
    logging.info(f"{datetime.datetime.now()} - character_select")
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker.name).order_by(Tracker.name.asc()))
            character = char_result.scalars().all()
        await engine.dispose()
        return character
    except NoResultFound:
        return []
    except Exception as e:
        logging.warning(f"character_select: {e}")
        return []


# Returns a list of all characters owned by the player, or all characters if the player is the GM
async def character_select_gm(ctx: discord.AutocompleteContext):
    # bughunt code
    logging.info(f"{datetime.datetime.now()} - attack_cog character_select_gm")
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    gm_status = await gm_check(ctx, engine)

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            if gm_status:
                char_result = await session.execute(select(Tracker.name).order_by(Tracker.name.asc()))
            else:
                char_result = await session.execute(
                    select(Tracker.name).where(Tracker.user == ctx.interaction.user.id).order_by(Tracker.name.asc())
                )
            character = char_result.scalars().all()
        await engine.dispose()
        return character
    except NoResultFound:
        return []
    except Exception as e:
        logging.warning(f"character_select_gm: {e}")
        return []


async def npc_select(ctx: discord.AutocompleteContext):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            char_result = await session.execute(
                select(Tracker.name).where(Tracker.player == false()).order_by(Tracker.name.asc())
            )
            character = char_result.scalars().all()
        await engine.dispose()
        return character
    except NoResultFound:
        return []
    except Exception as e:
        logging.warning(f"npc_select: {e}")
        return []


async def macro_select(ctx: discord.AutocompleteContext):
    character = ctx.options["character"]
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await initiative.get_guild(ctx, None)
    Tracker = await get_tracker(ctx, engine, id=guild.id)
    Macro = await get_macro(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with async_session() as session:
            char_result = await session.execute(select(Tracker.id).where(Tracker.name == character))
            char = char_result.scalars().one()

        async with async_session() as session:
            macro_result = await session.execute(
                select(Macro.name).where(Macro.character_id == char).order_by(Macro.name.asc())
            )
            macro_list = macro_result.scalars().all()
        await engine.dispose()
        return macro_list
    except Exception as e:
        logging.warning(f"a_macro_select: {e}")
        return []


async def a_macro_select(ctx: discord.AutocompleteContext):
    # bughunt code
    logging.info(f"{datetime.datetime.now()} - attack_cog a_macro_select")

    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    character = ctx.options["character"]
    guild = await initiative.get_guild(ctx, None)
    Tracker = await get_tracker(ctx, engine, id=guild.id)
    Macro = await get_macro(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    if guild.system == 'EPF':
        EPF_Char = await get_character(character, ctx, guild=guild, engine=engine)
        macro_list = await EPF_Char.macro_list()
        if ctx.value != "":
            val = ctx.value.lower()
            return [option for option in macro_list if val in option.lower()]
        else:
            return macro_list

    try:
        async with async_session() as session:
            char_result = await session.execute(select(Tracker.id).where(Tracker.name == character))
            char = char_result.scalars().one()
        async with async_session() as session:
            macro_result = await session.execute(
                select(Macro.name)
                    .where(Macro.character_id == char)
                    .where(not_(Macro.macro.contains(",")))
                    .order_by(Macro.name.asc())
            )
            macro_list = macro_result.scalars().all()
        await engine.dispose()
        return macro_list

    except NoResultFound:
        return []
    except Exception as e:
        logging.warning(f"a_macro_select: {e}")
        return []


async def cc_select(ctx: discord.AutocompleteContext):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    character = ctx.options["character"]

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await initiative.get_guild(ctx, None)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker.id).where(Tracker.name == character))
            char = char_result.scalars().one()
        async with async_session() as session:
            con_result = await session.execute(
                select(Condition.title)
                    .where(Condition.character_id == char)
                    .where(Condition.visible == true())
                    .order_by(Condition.title.asc())
            )
            condition = con_result.scalars().all()
        await engine.dispose()
        return condition
    except NoResultFound:
        return []
    except Exception as e:
        logging.warning(f"cc_select: {e}")
        return []


async def cc_select_no_time(ctx: discord.AutocompleteContext):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    character = ctx.options["character"]

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await initiative.get_guild(ctx, None)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker.id).where(Tracker.name == character))
            char = char_result.scalars().one()
        async with async_session() as session:
            con_result = await session.execute(
                select(Condition.title)
                    .where(Condition.character_id == char)
                    .where(Condition.time == false())
                    .where(Condition.visible == true())
                    .order_by(Condition.title.asc())
            )
            condition = con_result.scalars().all()
        await engine.dispose()
        return condition
    except NoResultFound:
        return []
    except Exception as e:
        logging.warning(f"cc_select: {e}")
        return []


async def save_select(ctx: discord.AutocompleteContext):
    try:
        guild = await initiative.get_guild(ctx, None)
        if guild.system == "PF2" or guild.system == "EPF":
            return PF2e.pf2_functions.PF2_saves
        else:
            return []
    except NoResultFound:
        return []
    except Exception as e:
        logging.warning(f"cc_select: {e}")
        return []
