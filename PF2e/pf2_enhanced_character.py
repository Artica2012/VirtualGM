# pf2_functions.py
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
from utils.utils import get_guild
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



# A class to hold the data model and functions involved in the enhanced pf2 features
class PF2_Character():
    def __init__(self, char_name, ctx: discord.ApplicationContext, bot: discord.Bot, guild=None):
        self.char_name = char_name
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    # Import the character data from pathbuilder. Create a new character if one does not exist, or update the existing
    # row if one does exist.
    async def pb_import(self, ctx, pb_char_code, guild=None):
        paramaters = {"id": pb_char_code}
        overwrite = False

        # Connect to pathbuilder
        async with aiohttp.ClientSession() as session:
            pb_url = "https://pathbuilder2e.com/json.php"
            async with session.get(pb_url, params=paramaters, verify_ssl=False) as resp:
                pb = await resp.json(content_type="text/html")

        if pb["success"] is False:
            return False

        guild = await get_guild(ctx, guild)
        PF2_tracker = await self.get_pf2_e_tracker(ctx, guild=guild)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        # Check to see if character already exists, if it does, update instead of creating
        async with async_session() as session:
            query = await session.execute(select(PF2_tracker).where(PF2_tracker.name == self.char_name))
            character = query.scalars().all()
        if len(character) > 0:
            overwrite = True

        lores = ""
        for item, value in pb["build"]["lores"]:
            output = f"{item}, {value}; "
            lores += output

        feats = ""
        for item in pb['build']['feats']:
            feats += f"{item}, "

        if overwrite:
            async with async_session() as session:
                query = await session.execute(select(PF2_tracker).where(PF2_tracker.name == self.char_name))
                character = query.scalars().one()

                # Write the data from the JSON
                character.max_hp = (
                        pb["build"]["attributes"]["ancestryhp"]
                        + pb["build"]["attributes"]["classhp"]
                        + pb["build"]["attributes"]["bonushp"]
                        + floor((pb["build"]["abilities"]["con"] - 10) / 2)
                        + (
                                (pb["build"]["level"] - 1)
                                * (
                                        pb["build"]["attributes"]["classhp"]
                                        + pb["build"]["attributes"]["bonushpPerLevel"]
                                        + floor((pb["build"]["abilities"]["con"] - 10) / 2)
                                )
                        )
                )
                character.char_class = pb["build"]["class"]
                character.level = pb["build"]["level"]
                character.ac_base = pb["build"]["acTotal"]['acTotal']
                character.class_dc = pb["build"]["proficiencies"]["classDC"]
                character.key_ability = pb["build"]["keyability"]

                character.str = pb["build"]["abilities"]["str"]
                character.dex = pb["build"]["abilities"]["dex"]
                character.con = pb["build"]["abilities"]["con"]
                character.itl = pb["build"]["abilities"]["int"]
                character.wis = pb["build"]["abilities"]["wis"]
                character.cha = pb["build"]["abilities"]["cha"]

                character.fort_prof = pb["build"]["proficiencies"]["fortitude"]
                character.reflex_prof = pb["build"]["proficiencies"]["reflex"]
                character.will_prof = pb["build"]["proficiencies"]["will"]

                character.unarmored_prof = pb["build"]["proficiencies"]["unarmored"]
                character.light_armor_prof = pb["build"]["proficiencies"]["light"]
                character.medium_armor_prof = pb["build"]["proficiencies"]["medium"]
                character.heavy_armor_prof = pb["build"]["proficiencies"]["heavy"]

                character.unarmed_prof = pb["build"]["proficiencies"]["unarmed"]
                character.simple_prof = pb["build"]["proficiencies"]["simple"]
                character.martial_prof = pb["build"]["proficiencies"]["martial"]
                character.advanced_prof = pb["build"]["proficiencies"]["advanced"]

                character.arcane_prof = pb["build"]["proficiencies"]["castingArcane"]
                character.divine_prof = pb["build"]["proficiencies"]["castingDivine"]
                character.occult_prof = pb["build"]["proficiencies"]["castingOccult"]
                character.primal_prof = pb["build"]["proficiencies"]["castingPrimal"]

                character.acrobatics_prof = pb["build"]["proficiencies"]["acrobatics"]
                character.arcana_prof = pb["build"]["proficiencies"]["arcana"]
                character.athletics_prof = pb["build"]["proficiencies"]["athletics"]
                character.crafting_prof = pb["build"]["proficiencies"]["crafting"]
                character.deception_prof = pb["build"]["proficiencies"]["deception"]
                character.diplomacy_prof = pb["build"]["proficiencies"]["diplomacy"]
                character.intimidation_prof = pb["build"]["proficiencies"]["intimidation"]
                character.medicine_prof = pb["build"]["proficiencies"]["medicine"]
                character.nature_prof = pb["build"]["proficiencies"]["nature"]
                character.occultism_prof = pb["build"]["proficiencies"]["occultism"]
                character.perception_prof = pb["build"]["proficiencies"]["perception"]
                character.performance_prof = pb["build"]["proficiencies"]["performance"]
                character.religion_prof = pb["build"]["proficiencies"]["religion"]
                character.society_prof = pb["build"]["proficiencies"]["society"]
                character.stealth_prof = pb["build"]["proficiencies"]["stealth"]
                character.survival_prof = pb["build"]["proficiencies"]["survival"]
                character.thievery_prof = pb["build"]["proficiencies"]["thievery"]

                character.lores = lores
                character.feats = feats

                await session.commit()

        else:  # Create a new character
            async with async_session() as session:
                async with session.begin():
                    new_char = PF2_tracker(
                        name=self.char_name,
                        player=True,
                        user=ctx.user.id,
                        current_hp=(
                                pb["build"]["attributes"]["ancestryhp"]
                                + pb["build"]["attributes"]["classhp"]
                                + pb["build"]["attributes"]["bonushp"]
                                + floor((pb["build"]["abilities"]["con"] - 10) / 2)
                                + (
                                        (pb["build"]["level"] - 1)
                                        * (
                                                pb["build"]["attributes"]["classhp"]
                                                + pb["build"]["attributes"]["bonushpPerLevel"]
                                                + floor((pb["build"]["abilities"]["con"] - 10) / 2)
                                        )
                                )
                        ),
                        max_hp=(
                                pb["build"]["attributes"]["ancestryhp"]
                                + pb["build"]["attributes"]["classhp"]
                                + pb["build"]["attributes"]["bonushp"]
                                + floor((pb["build"]["abilities"]["con"] - 10) / 2)
                                + (
                                        (pb["build"]["level"] - 1)
                                        * (
                                                pb["build"]["attributes"]["classhp"]
                                                + pb["build"]["attributes"]["bonushpPerLevel"]
                                                + floor((pb["build"]["abilities"]["con"] - 10) / 2)
                                        )
                                )
                        ),
                        temp_hp=0,

                        char_class=pb["build"]["class"],
                        level=pb["build"]["level"],
                        ac_total=pb["build"]["acTotal"]['acTotal'],
                        class_dc=pb["build"]["proficiencies"]["classDC"],

                        str=pb["build"]["abilities"]["str"],
                        dex=pb["build"]["abilities"]["dex"],
                        con=pb["build"]["abilities"]["con"],
                        itl=pb["build"]["abilities"]["int"],
                        wis=pb["build"]["abilities"]["wis"],
                        cha=pb["build"]["abilities"]["cha"],

                        fort_prof=pb["build"]["proficiencies"]["fortitude"],
                        reflex_prof=pb["build"]["proficiencies"]["reflex"],
                        will_prof=pb["build"]["proficiencies"]["will"],

                        unarmored_prof=pb["build"]["proficiencies"]["unarmored"],
                        light_armor_prof=pb["build"]["proficiencies"]["light"],
                        medium_armor_prof=pb["build"]["proficiencies"]["medium"],
                        heavy_armor_prof=pb["build"]["proficiencies"]["heavy"],

                        unarmed_prof=pb["build"]["proficiencies"]["unarmed"],
                        simple_prof=pb["build"]["proficiencies"]["simple"],
                        martial_prof=pb["build"]["proficiencies"]["martial"],
                        advanced_prof=pb["build"]["proficiencies"]["advanced"],

                        arcane_prof=pb["build"]["proficiencies"]["castingArcane"],
                        divine_prof=pb["build"]["proficiencies"]["castingDivine"],
                        occult_prof=pb["build"]["proficiencies"]["castingOccult"],
                        primal_prof=pb["build"]["proficiencies"]["castingPrimal"],

                        acrobatics_prof=pb["build"]["proficiencies"]["acrobatics"],
                        arcana_prof=pb["build"]["proficiencies"]["arcana"],
                        athletics_prof=pb["build"]["proficiencies"]["athletics"],
                        crafting_prof=pb["build"]["proficiencies"]["crafting"],
                        deception_prof=pb["build"]["proficiencies"]["deception"],
                        diplomacy_prof=pb["build"]["proficiencies"]["diplomacy"],
                        intimidation_prof=pb["build"]["proficiencies"]["intimidation"],
                        medicine_prof=pb["build"]["proficiencies"]["medicine"],
                        nature_prof=pb["build"]["proficiencies"]["nature"],
                        occultism_prof=pb["build"]["proficiencies"]["occultism"],
                        perception_prof=pb["build"]["proficiencies"]["perception"],

                        performance_prof=pb["build"]["proficiencies"]["performance"],
                        religion_prof=pb["build"]["proficiencies"]["religion"],
                        society_prof=pb["build"]["proficiencies"]["society"],
                        stealth_prof=pb["build"]["proficiencies"]["stealth"],
                        survival_prof=pb["build"]["proficiencies"]["survival"],
                        thievery_prof=pb["build"]["proficiencies"]["thievery"],

                        lores=lores,
                        feats=feats,
                    )
                    session.add(new_char)
                await session.commit()

    async def calculate(self, ctx, guild=None):
        # Database boilerplate
        guild = await get_guild(ctx, guild)
        PF2_tracker = await self.get_pf2_e_tracker(ctx, guild=guild)
        Condition = await get_condition(ctx, self.engine, id=guild.id)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        # Variables
        bonuses = {
            "circumstances_pos": {},
            "status_pos": {},
            "item_pos": {},
            "circumstances_neg": {},
            "status_neg": {},
            "item_neg": {}
        }

        # Iterate through conditions
        for condition in await self.conditions(ctx, guild):
            # Get the data from the conditions
            # Write the bonuses into the two dictionaries
            pass

        async with async_session() as session:
            query = await session.execute(select(PF2_tracker).where(PF2_tracker.name == self.char_name))
            character = query.scalars().one()

            # Go through each of the items.

            # Stat Mods - Do this first, because they are used in later calculations
            character.str_mod = await self.ability_mod_calc(character.str, "str", bonuses)
            character.dex_mod = await self.ability_mod_calc(character.str, "dex", bonuses)
            character.con_mod = await self.ability_mod_calc(character.str, "con", bonuses)
            character.itl_mod = await self.ability_mod_calc(character.str, "itl", bonuses)
            character.wis_mod = await self.ability_mod_calc(character.str, "wis", bonuses)
            character.cha_mod = await self.ability_mod_calc(character.str, "cha", bonuses)

            # Saves
            character.fort_mod = await self.save_mod_calc(character.con_mod, "fort", character.fort_prof,
                                                          character.level, bonuses)
            character.reflex_mod = await self.save_mod_calc(character.dex_mod, "reflex", character.reflex_prof,
                                                            character.level, bonuses)
            character.will_mod = await self.save_mod_calc(character.wis_mod, "wis", character.will_prof,
                                                          character.level, bonuses)

            # Skills
            character.athletics_prof = await self.skill_mod_calc(character.str_mod, "athletics",
                                                                 character.athletics_prof, character.level, bonuses)
            character.acrobatics_mod = await self.skill_mod_calc(character.dex_mod, "acrobatics",
                                                                 character.acrobatics_prof, character.level, bonuses)
            character.arcana_mod = await self.skill_mod_calc(character.itl_mod, "arcana",
                                                             character.arcana_prof, character.level, bonuses)
            character.crafting_mod = await self.skill_mod_calc(character.itl_mod, "crafting",
                                                               character.acrobatics_prof, character.level, bonuses)
            character.deception_mod = await self.skill_mod_calc(character.cha_mod, "deception",
                                                                character.deception_prof, character.level, bonuses)
            character.diplomacy_mod = await self.skill_mod_calc(character.cha_mod, "diplomacy",
                                                                character.diplomacy_prof, character.level, bonuses)
            character.intimidation_mod = await self.skill_mod_calc(character.cha_mod, "intimidation",
                                                                   character.intimidation_prof, character.level,
                                                                   bonuses)
            character.medicine_mod = await self.skill_mod_calc(character.wis_mod, "medicine",
                                                               character.medicine_prof, character.level, bonuses)
            character.nature_mod = await self.skill_mod_calc(character.wis_mod, "nature",
                                                             character.nature_prof, character.level, bonuses)
            character.occultism_mod = await self.skill_mod_calc(character.itl_mod, "occultism",
                                                                character.occultism_prof, character.level, bonuses)
            character.performance_mod = await self.skill_mod_calc(character.cha_mod, "performance",
                                                                  character.performance_prof, character.level, bonuses)
            character.religion_mod = await self.skill_mod_calc(character.wis_mod, "religion",
                                                               character.religion_prof, character.level, bonuses)
            character.society_mod = await self.skill_mod_calc(character.int_mod, "society",
                                                              character.society_prof, character.level, bonuses)
            character.stealth_mod = await self.skill_mod_calc(character.dex_mod, "stealth",
                                                                  character.stealth_prof, character.level, bonuses)
            character.survival_mod = await self.skill_mod_calc(character.wis_mod, "survival",
                                                                  character.survival_prof, character.level, bonuses)
            character.thievery_mod = await self.skill_mod_calc(character.dex_mod, "thievery",
                                                                  character.thievery_prof, character.level, bonuses)


            # Casting, Armor and Attacks
            key_ability = None
            match character.key_ability:
                case "str":
                    key_ability= character.str_mod
                case "dex":
                    key_ability = character.dex_mod
                case "con":
                    key_ability = character.con_mod
                case "int":
                    key_ability = character.itl_mod
                case "wis":
                    key_ability = character.wis_mod
                case "cha":
                    key_ability = character.cha_mod

            character.arcane_mod = await self.skill_mod_calc(key_ability, "arcane", character.arcane_prof,
                                                             character.level, bonuses)
            character.divine_mod = await self.skill_mod_calc(key_ability, "divine", character.divine_prof,
                                                             character.level, bonuses)
            character.occult_mod = await self.skill_mod_calc(key_ability, "occult", character.arcane_prof,
                                                             character.level, bonuses)
            character.primal_mod = await self.skill_mod_calc(key_ability, "primal", character.arcane_prof,
                                                             character.level, bonuses)

            character.ac_total = await self.bonus_calc(character.ac_base, "ac", bonuses)




    async def ability_mod_calc(self, base: int, item: str, bonuses):
        mod = (base - 10) / 2
        if item in bonuses["circumstances_pos"][item]:
            mod += bonuses["circumstances_pos"][item]
        if item in bonuses["circumstances_neg"][item]:
            mod -= bonuses["circumstances_neg"][item]

        if item in bonuses["status_pos"][item]:
            mod += bonuses["status_pos"][item]
        if item in bonuses["status_neg"][item]:
            mod -= bonuses["status_neg"][item]

        if item in bonuses["item_pos"][item]:
            mod += bonuses["item_pos"][item]
        if item in bonuses["item_neg"][item]:
            mod -= bonuses["item_neg"][item]

        return mod

    async def save_mod_calc(self, stat_mod, save: str, save_prof, level, bonuses):
        mod = stat_mod + save_prof + level
        if save in bonuses["circumstances_pos"][save]:
            mod += bonuses["circumstances_pos"][save]
        if save in bonuses["circumstances_neg"][save]:
            mod -= bonuses["circumstances_neg"][save]

        if save in bonuses["status_pos"][save]:
            mod += bonuses["status_pos"][save]
        if save in bonuses["status_neg"][save]:
            mod -= bonuses["status_neg"][save]

        if save in bonuses["item_pos"][save]:
            mod += bonuses["item_pos"][save]
        if save in bonuses["item_neg"][save]:
            mod -= bonuses["item_neg"][save]

        return mod

    async def skill_mod_calc(self, stat_mod, skill: str, skill_prof, level, bonuses):
        # TODO Throw in code for Untrained improvisation
        if skill_prof == 0:
            mod = stat_mod
        else:
            mod = stat_mod + skill_prof + level
        if skill in bonuses["circumstances_pos"][skill]:
            mod += bonuses["circumstances_pos"][skill]
        if skill in bonuses["circumstances_neg"][skill]:
            mod -= bonuses["circumstances_neg"][skill]

        if skill in bonuses["status_pos"][skill]:
            mod += bonuses["status_pos"][skill]
        if skill in bonuses["status_neg"][skill]:
            mod -= bonuses["status_neg"][skill]

        if skill in bonuses["item_pos"][skill]:
            mod += bonuses["item_pos"][skill]
        if skill in bonuses["item_neg"][skill]:
            mod -= bonuses["item_neg"][skill]

        return mod

    async def bonus_calc(self, base, skill, bonuses):
        mod = base
        if skill in bonuses["circumstances_pos"][skill]:
            mod += bonuses["circumstances_pos"][skill]
        if skill in bonuses["circumstances_neg"][skill]:
            mod -= bonuses["circumstances_neg"][skill]

        if skill in bonuses["status_pos"][skill]:
            mod += bonuses["status_pos"][skill]
        if skill in bonuses["status_neg"][skill]:
            mod -= bonuses["status_neg"][skill]

        if skill in bonuses["item_pos"][skill]:
            mod += bonuses["item_pos"][skill]
        if skill in bonuses["item_neg"][skill]:
            mod -= bonuses["item_neg"][skill]

        return mod

    async def character(self, ctx, guild=None):
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        PF2_tracker = await self.get_pf2_e_tracker(ctx, guild=guild)
        try:
            async with async_session() as session:
                result = await session.execute(select(PF2_tracker).where(PF2_tracker.name == self.char_name))
                return result.scalars().one()
        except NoResultFound:
            return None

    async def conditions(self, ctx, guild=None):
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        PF2_tracker = await self.get_pf2_e_tracker(ctx, guild=guild)
        if guild is not None:
            Condition = await get_condition(ctx, self.engine, id=guild.id)
        else:
            Condition = await get_condition(ctx, self.engine)
        try:
            async with async_session() as session:
                result = await session.execute(select(PF2_tracker.id).where(PF2_tracker.name == self.char_name))
                char_id = result.scalars().one()

            async with async_session() as session:
                result = await session.execute(select(Condition)
                                               .where(Condition.character_id == char_id))
                return result.scalars().all()
        except NoResultFound:
            return []

    async def get_pf2_e_tracker(self, ctx: discord.ApplicationContext, guild=None):
        if ctx is None and guild is None:
            raise Exception
        if guild is None:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            guild = await get_guild(ctx, guild)
        tablename = f"Tracker_{guild}"
        logging.info(f"get_pf2_e_tracker: Guild: {guild}")

        tablename = f"Tracker_{guild.id}"

        DynamicBase = declarative_base(class_registry=dict())

        class Tracker(DynamicBase):
            __tablename__ = tablename
            __table_args__ = {"extend_existing": True}

            # The original tracker table
            id = Column(Integer(), primary_key=True, autoincrement=True)
            name = Column(String(), nullable=False, unique=True)
            init = Column(Integer(), default=0)
            player = Column(Boolean(), nullable=False)
            user = Column(BigInteger(), nullable=False)
            current_hp = Column(Integer(), default=0)
            max_hp = Column(Integer(), default=1)
            temp_hp = Column(Integer(), default=0)
            init_string = Column(String(), nullable=True)
            active = Column(Boolean(), default=True)

            # General
            char_class = Column(String(), nullable=False)
            level = Column(Integer(), nullable=False)
            ac_base = Column(Integer(), nullable=False)
            class_dc = Column(Integer(), nullable=False)

            # Stats
            str = Column(Integer(), nullable=False)
            dex = Column(Integer(), nullable=False)
            con = Column(Integer(), nullable=False)
            itl = Column(Integer(), nullable=False)
            wis = Column(Integer(), nullable=False)
            cha = Column(Integer(), nullable=False)

            # Saves
            fort_prof = Column(Integer(), nullable=False)
            will_prof = Column(Integer(), nullable=False)
            reflex_prof = Column(Integer(), nullable=False)

            # Proficiencies
            perception_prof = Column(Integer(), nullable=False)
            class_prof = Column(Integer(), nullable=False)
            key_ability = Column(String(), nullable=False)

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

            # Plan to save parsable lists here
            lores = Column(String())
            feats = Column(String())

            # Calculated stats
            str_mod = Column(Integer())
            dex_mod = Column(Integer())
            con_mod = Column(Integer())
            itl_mod = Column(Integer())
            wis_mod = Column(Integer())
            cha_mod = Column(Integer())

            # Saves
            fort_mod = Column(Integer())
            will_mod = Column(Integer())
            reflex_mod = Column(Integer())

            acrobatics_mod = Column(Integer())
            arcana_mod = Column(Integer())
            athletics_mod = Column(Integer())
            crafting_mod = Column(Integer())
            deception_mod = Column(Integer())
            diplomacy_mod = Column(Integer())
            intimidation_mod = Column(Integer())
            medicine_mod = Column(Integer())
            nature_mod = Column(Integer())
            occultism_mod = Column(Integer())
            performance_mod = Column(Integer())
            religion_mod = Column(Integer())
            society_mod = Column(Integer())
            stealth_mod = Column(Integer())
            survival_mod = Column(Integer())
            thievery_mod = Column(Integer())

            arcane_mod = Column(Integer())
            divine_mod = Column(Integer())
            occult_mod = Column(Integer())
            primal_mod = Column(Integer())

            # unarmed_mod = Column(Integer())
            # simple_mod = Column(Integer())
            # martial_mod = Column(Integer())
            # advanced_mod = Column(Integer())

            ac_total = Column(Integer())
            resistance = Column(String())

        logging.info("get_tracker: returning tracker")
        return Tracker
