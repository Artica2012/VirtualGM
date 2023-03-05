# imports
import asyncio
import datetime
import inspect
import logging
import os
import sys

import d20
import discord

from dotenv import load_dotenv
from sqlalchemy import select, false
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# import D4e.d4e_functions
import PF2e.pf2_functions
import time_keeping_functions

from database_models import get_tracker, get_condition, get_macro
from error_handling_reporting import error_not_initialized, ErrorReport
# from initiative import get_guild, PF2AddCharacterModal, D4eAddCharacterModal, update_pinned_tracker
from utils.Char_Getter import get_character
from utils.utils import get_guild

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


