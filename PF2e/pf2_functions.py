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

