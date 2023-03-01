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
    get_pf2_e_tracker,
)
from database_operations import get_asyncio_db_engine
from character import Character
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


# Getter function for creation of the PF2_character class.  Necessary to load the character stats asynchronously on
# initialization of the class.
# If the stats haven't been computed, then the getter will run the calculate function before initialization
async def get_EPF_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating PF2_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    if guild is not None:
        PF2_tracker = await get_pf2_e_tracker(ctx, engine, id=guild.id)
    else:
        PF2_tracker = await get_pf2_e_tracker(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(PF2_tracker).where(PF2_tracker.name == char_name))
            character = result.scalars().one()
            if character.str_mod is None or character.nature_mod is None or character.ac_total is None:
                await calculate(ctx, engine, char_name, guild=guild)
                result = await session.execute(select(PF2_tracker).where(PF2_tracker.name == char_name))
                character = result.scalars().one()
            return PF2_Character(char_name, ctx, engine, character, guild=guild)

    except NoResultFound:
        return None


# A class to hold the data model and functions involved in the enhanced pf2 features
class PF2_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, guild=None):
        super().__init__(char_name, ctx, engine, character, guild)
        self.str_mod = character.str_mod
        self.dex_mod = character.dex_mod
        self.con_mod = character.con_mod
        self.itl_mod = character.itl_mod
        self.wis_mod = character.wis_mod
        self.cha_mod = character.cha_mod

        self.fort_mod = character.fort_mod
        self.reflex_mod = character.reflex_mod
        self.will_mod = character.will_mod

        self.acrobatics_mod = character.acrobatics_mod
        self.arcana_mod = character.arcana_mod
        self.athletics_mod = character.athletics_mod
        self.crafting_mod = character.crafting_mod
        self.deception_mod = character.deception_mod
        self.diplomacy_mod = character.diplomacy_mod
        self.intimidation_mod = character.intimidation_mod
        self.medicine_mod = character.medicine_mod
        self.nature_mod = character.nature_mod
        self.occultism_mod = character.occultism_mod
        self.perception_mod = character.perception_mod
        self.performance_mod = character.performance_mod
        self.religion_mod = character.religion_mod
        self.society_mod = character.society_mod
        self.stealth_mod = character.stealth_mod
        self.survival_mod = character.survival_mod
        self.thievery_mod = character.thievery_mod

        self.arcane_mod = character.arcane_mod
        self.divine_mod = character.divine_mod
        self.occult_mod = character.occult_mod
        self.primal_mod = character.primal_mod

        self.ac_total = character.ac_total
        self.resistance = character.resistance

    async def character(self):
        logging.info("Loading Character")
        if self.guild is not None:
            PF2_tracker = await get_pf2_e_tracker(self.ctx, self.engine, id=self.guild.id)
        else:
            PF2_tracker = await get_pf2_e_tracker(self.ctx, self.engine)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(select(PF2_tracker).where(PF2_tracker.name == self.char_name))
                character = result.scalars().one()
                if character.str_mod is None or character.nature_mod is None or character.ac_total is None:
                    await calculate(self.ctx, self.engine, self.char_name)
                    result = await session.execute(select(PF2_tracker).where(PF2_tracker.name == self.char_name))
                    character = result.scalars().one()
                return character

        except NoResultFound:
            return None

    async def update(self):
        logging.info(f"Updating character: {self.char_name}")
        await calculate(self.ctx, self.engine, self.char_name, guild=self.guild)
        self.character_model = await self.character()
        self.char_name = self.character_model.name
        self.id = self.character_model.id
        self.name = self.character_model.name
        self.player = self.character_model.player
        self.user = self.character_model.user
        self.current_hp = self.character_model.current_hp
        self.max_hp = self.character_model.max_hp
        self.temp_hp = self.character_model.max_hp
        self.init_string = self.character_model.init_string
        self.init = self.character_model.init

        self.str_mod = self.character_model.str_mod
        self.dex_mod = self.character_model.dex_mod
        self.con_mod = self.character_model.con_mod
        self.itl_mod = self.character_model.itl_mod
        self.wis_mod = self.character_model.wis_mod
        self.cha_mod = self.character_model.cha_mod

        self.fort_mod = self.character_model.fort_mod
        self.reflex_mod = self.character_model.reflex_mod
        self.will_mod = self.character_model.will_mod

        self.acrobatics_mod = self.character_model.acrobatics_mod
        self.arcana_mod = self.character_model.arcana_mod
        self.athletics_mod = self.character_model.athletics_mod
        self.crafting_mod = self.character_model.crafting_mod
        self.deception_mod = self.character_model.deception_mod
        self.diplomacy_mod = self.character_model.diplomacy_mod
        self.intimidation_mod = self.character_model.intimidation_mod
        self.medicine_mod = self.character_model.medicine_mod
        self.nature_mod = self.character_model.nature_mod
        self.occultism_mod = self.character_model.occultism_mod
        self.perception_mod = self.character_model.perception_mod
        self.performance_mod = self.character_model.performance_mod
        self.religion_mod = self.character_model.religion_mod
        self.society_mod = self.character_model.society_mod
        self.stealth_mod = self.character_model.stealth_mod
        self.survival_mod = self.character_model.survival_mod
        self.thievery_mod = self.character_model.thievery_mod

        self.arcane_mod = self.character_model.arcane_mod
        self.divine_mod = self.character_model.divine_mod
        self.occult_mod = self.character_model.occult_mod
        self.primal_mod = self.character_model.primal_mod

        self.ac_total = self.character_model.ac_total
        self.resistance = self.character_model.resistance

    async def get_roll(self, item):
        logging.info(f"Returning roll: {item}")
        if item == "Fortitude" or "Fort":
            return f"1d20+{self.fort_mod}"
        elif item == "Reflex":
            return f"1d20+{self.reflex_mod}"
        elif item == "Will":
            return f"1d20+{self.will_mod}"
        elif item == "Acrobatics":
            return f"1d20+{self.acrobatics_mod}"
        elif item == "Arcana":
            return f"1d20+{self.arcana_mod}"
        elif item == "Athletics":
            return f"1d20+{self.athletics_mod}"
        elif item == "Crafting":
            return f"1d20+{self.crafting_mod}"
        elif item == "Deception":
            return f"1d20+{self.deception_mod}"
        elif item == "Diplomacy":
            return f"1d20+{self.diplomacy_mod}"
        elif item == "Intimidation":
            return f"1d20+{self.intimidation_mod}"
        elif item == "Medicine":
            return f"1d20+{self.medicine_mod}"
        elif item == "Nature":
            return f"1d20+{self.nature_mod}"
        elif item == "Occultism":
            return f"1d20+{self.occult_mod}"
        elif item == "Perception":
            return f"1d20+{self.perception_mod}"
        elif item == "Performance":
            return f"1d20+{self.performance_mod}"
        elif item == "Religion":
            return f"1d20+{self.religion_mod}"
        elif item == "Society":
            return f"1d20+{self.society_mod}"
        elif item == "Stealth":
            return f"1d20+{self.stealth_mod}"
        elif item == "Survival":
            return f"1d20+{self.survival_mod}"
        elif item == "Thievery":
            return f"1d20+{self.thievery_mod}"
        else:
            for weapon in self.character_model.attacks:
                # print(item)
                # print(weapon["display"])
                if item == weapon["display"]:
                    proficiency = 0
                    match weapon["prof"]:
                        case "unarmed":
                            proficiency = self.character_model.unarmed_prof
                        case "simple":
                            proficiency = self.character_model.simple_prof
                        case "martial":
                            proficiency = self.character_model.martial_prof
                        case "advanced":
                            proficiency = self.character_model.advanced_prof
                    if proficiency > 0:
                        attack_mod = self.str_mod + self.character_model.level + proficiency + weapon["pot"]
                    else:
                        attack_mod = self.str_mod
                    # print(attack_mod)
                    return f"1d20+{attack_mod}"
            for attack in self.character_model.spells:
                # print(item)
                # print(attack["name"])
                if attack["name"] in item:
                    stat_mod = 0
                    match attack["ability"]:
                        case "con":
                            stat_mod = self.con_mod
                        case "int":
                            stat_mod = self.itl_mod
                        case "wis":
                            stat_mod = self.wis_mod
                        case "cha":
                            stat_mod = self.cha_mod

                    if attack["proficiency"] > 0:
                        attack_mod = stat_mod + self.character_model.level + attack["proficiency"]
                    else:
                        attack_mod = stat_mod
                    # print(attack_mod)
                    return f"1d20+{attack_mod}"
            return 0

    async def get_dc(self, item):
        if item == "AC":
            return self.ac_total
        elif item == "Fort":
            return 10 + self.fort_mod
        elif item == "Reflex":
            return 10 + self.reflex_mod
        elif item == "Will":
            return 10 + self.will_mod
        elif item == "DC":
            return 10 + self.character_model.class_dc
        elif item.lower() == "acrobatics":
            return 10 + self.acrobatics_mod
        elif item.lower() == "arcana":
            return 10 + self.arcana_mod
        elif item.lower() == "athletics":
            return 10 + self.athletics_mod
        elif item.lower() == "crafting":
            return 10 + self.crafting_mod
        elif item.lower() == "deception":
            return 10 + self.deception_mod
        elif item.lower() == "intimidation":
            return 10 + self.intimidation_mod
        elif item.lower() == "medicine":
            return 10 + self.medicine_mod
        elif item.lower() == "nature":
            return 10 + self.nature_mod
        elif item.lower() == "occultism":
            return 10 + self.occultism_mod
        elif item.lower() == "perception":
            return 10 + self.perception_mod
        elif item.lower() == "performance":
            return 10 + self.performance_mod
        elif item.lower() == "religion":
            return 10 + self.religion_mod
        elif item.lower() == "society":
            return 10 + self.society_mod
        elif item.lower() == "stealth":
            return 10 + self.stealth_mod
        elif item.lower() == "survival":
            return 10 + self.survival_mod
        elif item.lower() == "thievery":
            return 10 + self.thievery_mod
        else:
            return 0

    async def macro_list(self):
        list = self.character_model.macros.split(",")
        logging.info(list)
        if len(list) > 0:
            return list[:-1]
        else:
            return []

    async def conditions(self, ctx):
        logging.info("Returning PF2 Character Conditions")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        if self.guild is not None:
            Condition = await get_condition(ctx, self.engine, id=self.guild.id)
        else:
            Condition = await get_condition(ctx, self.engine)
        try:
            async with async_session() as session:
                result = await session.execute(select(Condition)
                                               .where(Condition.character_id == self.id))
                return result.scalars().all()
        except NoResultFound:
            return []


async def pb_import(ctx, engine, char_name, pb_char_code, guild=None):
    paramaters = {"id": pb_char_code}
    overwrite = False

    # Connect to pathbuilder
    async with aiohttp.ClientSession() as session:
        pb_url = "https://pathbuilder2e.com/json.php"
        async with session.get(pb_url, params=paramaters, verify_ssl=False) as resp:
            pb = await resp.json(content_type="text/html")

    if pb["success"] is False:
        return False

    # try:
    guild = await get_guild(ctx, guild)
    PF2_tracker = await get_pf2_e_tracker(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Check to see if character already exists, if it does, update instead of creating
    async with async_session() as session:
        query = await session.execute(select(PF2_tracker).where(PF2_tracker.name == char_name))
        character = query.scalars().all()
    if len(character) > 0:
        overwrite = True

    lores = ""
    for item, value in pb["build"]["lores"]:
        output = f"{item}, {value}; "
        lores += output

    feats = ""
    for item in pb['build']['feats']:
        feats += f"{item[0]}, "

    if overwrite:
        async with async_session() as session:
            query = await session.execute(select(PF2_tracker).where(PF2_tracker.name == char_name))
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
            character.class_prof = pb["build"]["proficiencies"]["classDC"]
            character.class_dc = 0
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
            character.attacks = pb["build"]["weapons"]
            character.spells = pb["build"]["spellCasters"]

            await session.commit()
        return True

    else:  # Create a new character
        async with async_session() as session:
            async with session.begin():
                new_char = PF2_tracker(
                    name=char_name,
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
                    ac_base=pb["build"]["acTotal"]['acTotal'],
                    class_prof=pb["build"]["proficiencies"]["classDC"],
                    class_dc=0,

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
                    key_ability=pb["build"]["keyability"],
                    attacks=pb["build"]["weapons"],
                    spells=pb["build"]["spellCasters"],
                )
                session.add(new_char)
            await session.commit()
            return True
    # except Exception:
    #     return False


async def calculate(ctx, engine, char_name, guild=None):
    logging.info('Updating Character Model')
    guild = await get_guild(ctx, guild=guild)
    # Database boilerplate
    if guild is not None:
        PF2_tracker = await get_pf2_e_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
    else:
        PF2_tracker = await get_pf2_e_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

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
    try:
        async with async_session() as session:
            result = await session.execute(select(PF2_tracker.id).where(PF2_tracker.name == char_name))
            char_id = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(select(Condition)
                                           .where(Condition.character_id == char_id))
            conditions = result.scalars().all()
    except NoResultFound:
        conditions = []

    for condition in conditions:
        # Get the data from the conditions
        # Write the bonuses into the two dictionaries
        pass

    async with async_session() as session:
        # try:
        query = await session.execute(select(PF2_tracker).where(PF2_tracker.name == char_name))
        character = query.scalars().one()

        # Go through each of the items.

        # Stat Mods - Do this first, because they are used in later calculations
        character.str_mod = await ability_mod_calc(character.str, "str", bonuses)
        character.dex_mod = await ability_mod_calc(character.dex, "dex", bonuses)
        character.con_mod = await ability_mod_calc(character.con, "con", bonuses)
        character.itl_mod = await ability_mod_calc(character.itl, "itl", bonuses)
        character.wis_mod = await ability_mod_calc(character.wis, "wis", bonuses)
        character.cha_mod = await ability_mod_calc(character.cha, "cha", bonuses)

        # Saves
        character.fort_mod = await save_mod_calc(character.con_mod, "fort", character.fort_prof,
                                                 character.level, bonuses)
        character.reflex_mod = await save_mod_calc(character.dex_mod, "reflex", character.reflex_prof,
                                                   character.level, bonuses)
        character.will_mod = await save_mod_calc(character.wis_mod, "wis", character.will_prof,
                                                 character.level, bonuses)

        # Skills
        character.athletics_mod = await skill_mod_calc(character.str_mod, "athletics",
                                                       character.athletics_prof, character.level, bonuses)
        character.acrobatics_mod = await skill_mod_calc(character.dex_mod, "acrobatics",
                                                        character.acrobatics_prof, character.level,
                                                        bonuses)
        character.arcana_mod = await skill_mod_calc(character.itl_mod, "arcana",
                                                    character.arcana_prof, character.level, bonuses)
        character.crafting_mod = await skill_mod_calc(character.itl_mod, "crafting",
                                                      character.acrobatics_prof, character.level, bonuses)
        character.deception_mod = await skill_mod_calc(character.cha_mod, "deception",
                                                       character.deception_prof, character.level, bonuses)
        character.diplomacy_mod = await skill_mod_calc(character.cha_mod, "diplomacy",
                                                       character.diplomacy_prof, character.level, bonuses)
        character.intimidation_mod = await skill_mod_calc(character.cha_mod, "intimidation",
                                                          character.intimidation_prof, character.level,
                                                          bonuses)
        character.medicine_mod = await skill_mod_calc(character.wis_mod, "medicine",
                                                      character.medicine_prof, character.level, bonuses)
        character.nature_mod = await skill_mod_calc(character.wis_mod, "nature",
                                                    character.nature_prof, character.level, bonuses)
        character.occultism_mod = await skill_mod_calc(character.itl_mod, "occultism",
                                                       character.occultism_prof, character.level, bonuses)
        character.perception_mod = await skill_mod_calc(character.wis_mod, "perception",
                                                        character.perception_prof, character.level,
                                                        bonuses)
        character.performance_mod = await skill_mod_calc(character.cha_mod, "performance",
                                                         character.performance_prof, character.level,
                                                         bonuses)
        character.religion_mod = await skill_mod_calc(character.wis_mod, "religion",
                                                      character.religion_prof, character.level, bonuses)
        character.society_mod = await skill_mod_calc(character.itl_mod, "society",
                                                     character.society_prof, character.level, bonuses)
        character.stealth_mod = await skill_mod_calc(character.dex_mod, "stealth",
                                                     character.stealth_prof, character.level, bonuses)
        character.survival_mod = await skill_mod_calc(character.wis_mod, "survival",
                                                      character.survival_prof, character.level, bonuses)
        character.thievery_mod = await skill_mod_calc(character.dex_mod, "thievery",
                                                      character.thievery_prof, character.level, bonuses)

        # Casting, Armor and Attacks
        key_ability = None
        match character.key_ability:
            case "str":
                key_ability = character.str_mod
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

        character.arcane_mod = await skill_mod_calc(key_ability, "arcane", character.arcane_prof,
                                                    character.level, bonuses)
        character.divine_mod = await skill_mod_calc(key_ability, "divine", character.divine_prof,
                                                    character.level, bonuses)
        character.occult_mod = await skill_mod_calc(key_ability, "occult", character.arcane_prof,
                                                    character.level, bonuses)
        character.primal_mod = await skill_mod_calc(key_ability, "primal", character.arcane_prof,
                                                    character.level, bonuses)

        character.ac_total = await bonus_calc(character.ac_base, "ac", bonuses)
        character.class_dc = await skill_mod_calc(key_ability, "class_dc", character.class_prof, character.level,
                                                  bonuses)
        character.init_string = f"1d20+{character.perception_mod}"

        macros = []
        for item in character.attacks:
            macros.append(item["display"])
        for item in character.spells:
            macros.append(f"Spell Attack: {item['name']}")
        macros.extend(PF2_skills)
        macro_string = ""
        for item in macros:
            macro_string += f"{item},"
        character.macros = macro_string

        await session.commit()

        # except Exception as e:
        #     logging.warning(f"pf2 - enchanced character importer: {e}")


async def ability_mod_calc(base: int, item: str, bonuses):
    mod = floor((base - 10) / 2)
    if item in bonuses["circumstances_pos"]:
        mod += bonuses["circumstances_pos"][item]
    if item in bonuses["circumstances_neg"]:
        mod -= bonuses["circumstances_neg"][item]

    if item in bonuses["status_pos"]:
        mod += bonuses["status_pos"][item]
    if item in bonuses["status_neg"]:
        mod -= bonuses["status_neg"][item]

    if item in bonuses["item_pos"]:
        mod += bonuses["item_pos"][item]
    if item in bonuses["item_neg"]:
        mod -= bonuses["item_neg"][item]

    return mod


async def save_mod_calc(stat_mod, save: str, save_prof, level, bonuses):
    mod = stat_mod + save_prof + level
    if save in bonuses["circumstances_pos"]:
        mod += bonuses["circumstances_pos"][save]
    if save in bonuses["circumstances_neg"]:
        mod -= bonuses["circumstances_neg"][save]

    if save in bonuses["status_pos"]:
        mod += bonuses["status_pos"][save]
    if save in bonuses["status_neg"]:
        mod -= bonuses["status_neg"][save]

    if save in bonuses["item_pos"]:
        mod += bonuses["item_pos"][save]
    if save in bonuses["item_neg"]:
        mod -= bonuses["item_neg"][save]

    return mod


async def skill_mod_calc(stat_mod, skill: str, skill_prof, level, bonuses):
    # TODO Throw in code for Untrained improvisation
    if skill_prof == 0:
        mod = stat_mod
    else:
        mod = stat_mod + skill_prof + level
    if skill in bonuses["circumstances_pos"]:
        mod += bonuses["circumstances_pos"][skill]
    if skill in bonuses["circumstances_neg"]:
        mod -= bonuses["circumstances_neg"][skill]

    if skill in bonuses["status_pos"]:
        mod += bonuses["status_pos"][skill]
    if skill in bonuses["status_neg"]:
        mod -= bonuses["status_neg"][skill]

    if skill in bonuses["item_pos"]:
        mod += bonuses["item_pos"][skill]
    if skill in bonuses["item_neg"]:
        mod -= bonuses["item_neg"][skill]

    return mod


async def bonus_calc(base, skill, bonuses):
    mod = base
    if skill in bonuses["circumstances_pos"]:
        mod += bonuses["circumstances_pos"][skill]
    if skill in bonuses["circumstances_neg"]:
        mod -= bonuses["circumstances_neg"][skill]

    if skill in bonuses["status_pos"]:
        mod += bonuses["status_pos"][skill]
    if skill in bonuses["status_neg"]:
        mod -= bonuses["status_neg"][skill]

    if skill in bonuses["item_pos"]:
        mod += bonuses["item_pos"][skill]
    if skill in bonuses["item_neg"]:
        mod -= bonuses["item_neg"][skill]

    return mod
