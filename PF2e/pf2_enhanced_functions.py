import asyncio
import logging
import os

# imports
from datetime import datetime
from math import floor

import aiohttp
import discord
from discord import Interaction
from dotenv import load_dotenv
import sqlalchemy as db
from sqlalchemy import select, false, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, BigInteger
from sqlalchemy import String, Boolean
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

import d20

from PF2e.pf2_functions import PF2_eval_succss
from PF2e.pf2_enhanced_character import get_PF2_Character
from utils.utils import get_guild
from database_models import (
    get_condition,
    get_pf2_e_tracker,
)
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, get_time
from utils.parsing import ParseModifiers

# define global variables

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

PF2_attributes = ["AC", "Fort", "Reflex", "Will", "DC"]
PF2_saves = ["Fort", "Reflex", "Will"]
PF2_base_dc = 10
PF2_skills = ["Acrobatics", "Arcana", "Athletics", "Crafting", "Deception", "Diplomacy", "Intimidation", "Medicine",
              "Nature", "Occultism", "Perception", "Performance", "Religion", "Society", "Stealth", "Survival",
              "Thievery"]


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
    try:
        # if type(roll[0]) == int:
        roll_string: str = f"{roll}{ParseModifiers(attack_modifier)}"
        print(roll_string)
        dice_result = d20.roll(roll_string)
        # else:
        #     char_model = await get_PF2_Character(character, ctx, engine=engine)
        #     roll_string = await char_model.get_roll(roll)
        #     print(roll_string)
        #     dice_result = d20.roll(roll_string)
    except:
        char_model = await get_PF2_Character(character, ctx, engine=engine)
        roll_string = f"{await char_model.get_roll(roll)}{ParseModifiers(attack_modifier)}"
        print(roll_string)
        dice_result = d20.roll(roll_string)
    # print(f"{dice_result}")

    # Load up the tables
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    # Throwing guild in here will allow one database query instead of two for getting the tables
    opponent = await get_PF2_Character(target, ctx, engine=engine)
    goal_value = await opponent.get_dc(vs)

    try:
        logging.info(f"Target Modifier: {target_modifier}")
        goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
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
