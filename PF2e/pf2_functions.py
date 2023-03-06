# pf2_functions.py
import asyncio
import logging
import os

# imports
from datetime import datetime

import discord
from discord import Interaction
from dotenv import load_dotenv
from sqlalchemy import select, false, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import d20

import Base.character_functions
# import initiative
from database_models import (
    get_condition,
    get_tracker,
)
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, get_time
from utils.parsing import ParseModifiers
from utils.utils import get_guild

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

PF2_attributes = ["AC", "Fort", "Reflex", "Will", "DC"]
PF2_saves = ["Fort", "Reflex", "Will"]
PF2_base_dc = 10


async def attack(
    ctx: discord.ApplicationContext,
    engine,
    bot,
    character: str,
    target: str,
    roll: str,
    vs: str,
    attack_modifier: str,
    target_modifier: str,
):
    # Strip a macro:
    roll_list = roll.split(":")
    # print(roll_list)
    if len(roll_list) == 1:
        roll = roll
    else:
        roll = roll_list[1]

    roll_string: str = f"({roll}){ParseModifiers(attack_modifier)}"
    dice_result = d20.roll(roll_string)
    # print(f"{dice_result}")


    # Load up the tables
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    # Throwing guild in here will allow one database query instead of two for getting the tables
    guild = await get_guild(ctx, None)
    Tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)

    # Load the target character
    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker.id).where(Tracker.name == target))
            targ = result.scalars().one()

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"attack: {e}")
        report = ErrorReport(ctx, "/attack (emp)", e, bot)
        await report.report()
        return False

    try:
        # Load the value of the target condition - just need the number here
        async with async_session() as session:
            result = await session.execute(
                select(Condition.number).where(Condition.character_id == targ).where(Condition.title == vs)
            )
            con_vs = result.scalars().one()

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"get_cc: {e}")
        report = ErrorReport(ctx, "/attack (con)", e, bot)
        await report.report()
        return False

    goal_value = con_vs + (PF2_base_dc if vs in ["Fort", "Will", "Reflex"] else 0)

    try:
        logging.info(f"Target Modifier: {target_modifier}")
        goal_string: str = f"({goal_value}){ParseModifiers(target_modifier)}"
        logging.info(f"Goal: {goal_string}")
        goal_result = d20.roll(goal_string)
        # print(f"{dice_result}")
    except Exception as e:
        logging.warning(f"attack: {e}")
        report = ErrorReport(ctx, "/attack (emp)", e, bot)
        await report.report()
        return False

    # Format output string
    success_string = PF2_eval_succss(dice_result, goal_result)
    output_string = f"{character} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
    return output_string


async def save(
    ctx: discord.ApplicationContext, engine, bot, character: str, target: str, vs: str, dc: int, modifier: str
):
    if target is None:
        output_string = "Error. No Target Specified."
        return output_string

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    guild = await get_guild(ctx, None)
    Tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    orig_dc = dc
    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker.id).where(Tracker.name == character))
            char = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(select(Tracker.id).where(Tracker.name == target))
            targ = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == targ).where(Condition.title == vs)
            )
            raw_roll = result.scalars().one()
            roll = f"1d20+{raw_roll.number}"

        if dc is None:
            async with async_session() as session:
                result = await session.execute(
                    select(Condition.number).where(Condition.character_id == char).where(Condition.title == "DC")
                )
                dc = result.scalars().one()

        try:
            dice_result = d20.roll(roll)
            goal_string: str = f"{dc}{ParseModifiers(modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"attack: {e}")
            await ErrorReport(ctx, "/attack (emp)", e, bot).report()
            return False

        success_string = PF2_eval_succss(dice_result, goal_result)
        # Format output string
        if character == target:
            output_string = f"{character} makes a {vs} save!\n{dice_result}\n{success_string if orig_dc else ''}"
        else:
            output_string = (
                f"{target} makes a {vs} save!\n{character} forced the save.\n{dice_result}\n{success_string}"
            )

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"attack: {e}")
        report = ErrorReport(ctx, "/attack (emp)", e, bot)
        await report.report()
        return False

    return output_string


def PF2_eval_succss(dice_result: d20.RollResult, goal: d20.RollResult):
    success_string = ""
    if dice_result.total >= goal.total + PF2_base_dc:
        result_tier = 4
    elif dice_result.total >= goal.total:
        result_tier = 3
    elif goal.total >= dice_result.total >= goal.total - 9:
        result_tier = 2
    else:
        result_tier = 1

    match dice_result.crit:
        case d20.CritType.CRIT:
            result_tier += 1
        case d20.CritType.FAIL:
            result_tier -= 1

    if result_tier >= 4:
        success_string = "Critical Success"
    elif result_tier == 3:
        success_string = "Success"
    elif result_tier == 2:
        success_string = "Failure"
    else:
        success_string = "Critical Failure"

    return success_string

