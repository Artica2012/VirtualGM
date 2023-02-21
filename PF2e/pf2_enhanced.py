# pf2_functions.py
import asyncio
import logging
import os

# imports
from datetime import datetime

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
import initiative
from database_models import (
    get_condition,
    get_tracker,
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

class PF2_Character():
    def __init__(self, char_name, ctx: discord.ApplicationContext, bot:discord.Bot, guild=None):
        self.char_name = char_name
        self.engine =  get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    async def pb_import(self,pb_char_code ):
        paramaters = {"id": pb_char_code}

        async with aiohttp.ClientSession() as session:
            pb_url = "https://pathbuilder2e.com/json.php"
            async with session.get(pb_url, params=paramaters, verify_ssl=False) as resp:
                pb = await resp.json(content_type="text/html")

        if pb["success"] is False:
            return False

    async def get_pf2_e_tracker(self, ctx: discord.ApplicationContext, guild=None):
        if ctx is None and guild is None:
            raise Exception
        if guild is None:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            guild = await initiative.get_guild(ctx, guild)
        tablename = f"Tracker_{guild}"
        logging.info(f"get_pf2_e_tracker: Guild: {guild}")

        tablename = f"Tracker_{guild.id}"

        DynamicBase = declarative_base(class_registry=dict())

        class Tracker(DynamicBase):
            __tablename__ = tablename
            __table_args__ = {"extend_existing": True}

            id = Column(Integer(), primary_key=True, autoincrement=True)
            name = Column(String(), nullable=False, unique=True)
            # init = Column(Integer(), default=0)
            player = Column(Boolean(), nullable=False)
            user = Column(BigInteger(), nullable=False)
            current_hp = Column(Integer(), default=0)
            max_hp = Column(Integer(), default=1)
            temp_hp = Column(Integer(), default=0)
            # init_string = Column(String(), nullable=True)
            active = Column(Boolean(), default=True)

            char_class = Column(String(), nullable=False)
            level = Column(Integer(), nullable=False)


            str = Column(Integer(), nullable=False)
            dex = Column(Integer(), nullable=False)
            con = Column(Integer(), nullable=False)
            inl = Column(Integer(), nullable=False)
            wis = Column(Integer(), nullable=False)
            cha = Column(Integer(), nullable=False)

            fort_prof = Column(Integer(), nullable=False)
            will_prof = Column(Integer(), nullable=False)
            reflex_prof = Column(Integer(), nullable=False)

            perception_prof = Column(Integer(), nullable=False)
            class_prof = Column(Integer(), nullable=False)

            unarmored_prof = Column(Integer(), nullable=False)
            light_armor_prof = Column(Integer(), nullable=False)
            medium_armor_prof = Column(Integer(), nullable=False)
            heavy_armor_prof = Column(Integer(), nullable=False)

            unarmed_prof = Column(Integer(), nullable=False)
            simple_prof = Column(Integer(), nullable=False)
            martial_prof = Column(Integer(), nullable=False)
            advanced_prof = Column(Integer(), nullable=False)

            arcane_prof = Column(Integer(), nullable=False)
            divine_prof = Column(Integer(), nullable=False)
            occult_prof = Column(Integer(), nullable=False)
            primal_prof = Column(Integer(), nullable=False)

            acrobatics_prof = Column(Integer(), nullable=False)
            arcana_prof = Column(Integer(), nullable=False)
            athletics_prof = Column(Integer(), nullable=False)
            crafting_prof = Column(Integer(), nullable=False)
            deception_prof = Column(Integer(), nullable=False)
            diplomacy_prof = Column(Integer(), nullable=False)
            intimidation_prof = Column(Integer(), nullable=False)
            medicine_prof = Column(Integer(), nullable=False)
            nature_prof = Column(Integer(), nullable=False)
            occultism_prof = Column(Integer(), nullable=False)
            performance_prof = Column(Integer(), nullable=False)
            religion_prof = Column(Integer(), nullable=False)
            society_prof = Column(Integer(), nullable=False)
            stealth_prof = Column(Integer(), nullable=False)
            survival_prof = Column(Integer(), nullable=False)
            thievery_prof = Column(Integer(), nullable=False)
            lores = Column(String())

            feats = Column(String())
            ac_total = Column(Integer(), nullable=False)












        logging.info("get_tracker: returning tracker")
        return Tracker
