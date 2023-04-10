# pf2_functions.py
import asyncio
import logging
import math
import os

# imports
import datetime
from math import floor

import aiohttp
import discord
from dotenv import load_dotenv
from sqlalchemy import true, Column, Integer, String, JSON, false, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_session
from sqlalchemy.orm import sessionmaker

import d20

import EPF.EPF_Support
import time_keeping_functions
from utils.utils import get_guild
from database_models import (
    get_condition,
    get_EPF_tracker,
    Base,
    get_macro,
)
from database_operations import get_asyncio_db_engine, DATABASE
from Base.Character import Character
from error_handling_reporting import error_not_initialized
from time_keeping_functions import get_time
from utils.parsing import ParseModifiers
from EPF.EPF_Support import EPF_Conditions, EPF_SKills, EPF_SKills_NO_SAVE
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA

# define global variables

PF2_attributes = ["AC", "Fort", "Reflex", "Will", "DC"]
PF2_saves = ["Fort", "Reflex", "Will"]
PF2_base_dc = 10
PF2_skills = [
    "Acrobatics",
    "Arcana",
    "Athletics",
    "Crafting",
    "Deception",
    "Diplomacy",
    "Intimidation",
    "Medicine",
    "Nature",
    "Occultism",
    "Perception",
    "Performance",
    "Religion",
    "Society",
    "Stealth",
    "Survival",
    "Thievery",
]


# Getter function for creation of the PF2_character class.  Necessary to load the character stats asynchronously on
# initialization of the class.
# If the stats haven't been computed, then the getter will run the calculate function before initialization
async def get_EPF_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating PF2_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    EPF_tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(EPF_tracker).where(EPF_tracker.name == char_name))
            character = result.scalars().one()
            if character.str_mod is None or character.nature_mod is None or character.ac_total is None:
                await calculate(ctx, engine, char_name, guild=guild)
                result = await session.execute(select(EPF_tracker).where(EPF_tracker.name == char_name))
                character = result.scalars().one()
            return EPF_Character(char_name, ctx, engine, character, guild=guild)

    except NoResultFound:
        return None


# A class to hold the data model and functions involved in the enhanced pf2 features
class EPF_Character(Character):
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
            PF2_tracker = await get_EPF_tracker(self.ctx, self.engine, id=self.guild.id)
        else:
            PF2_tracker = await get_EPF_tracker(self.ctx, self.engine)
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
        print(item)
        if item == "Fortitude" or item == "Fort":
            print("a")
            return f"1d20+{self.fort_mod}"
        elif item == "Reflex":
            print("b")
            return f"1d20+{self.reflex_mod}"
        elif item == "Will":
            print("c")
            return f"1d20+{self.will_mod}"
        elif item == "Acrobatics":
            print("d")
            return f"1d20+{self.acrobatics_mod}"
        elif item == "Arcana":
            print("e")
            return f"1d20+{self.arcana_mod}"
        elif item == "Athletics":
            print("f")
            return f"1d20+{self.athletics_mod}"
        elif item == "Crafting":
            print("g")
            return f"1d20+{self.crafting_mod}"
        elif item == "Deception":
            print("h")
            return f"1d20+{self.deception_mod}"
        elif item == "Diplomacy":
            print("i")
            return f"1d20+{self.diplomacy_mod}"
        elif item == "Intimidation":
            print("j")
            return f"1d20+{self.intimidation_mod}"
        elif item == "Medicine":
            print("k")
            return f"1d20+{self.medicine_mod}"
        elif item == "Nature":
            print("l")
            return f"1d20+{self.nature_mod}"
        elif item == "Occultism":
            print("m")
            return f"1d20+{self.occult_mod}"
        elif item == "Perception":
            print("n")
            return f"1d20+{self.perception_mod}"
        elif item == "Performance":
            print("o")
            return f"1d20+{self.performance_mod}"
        elif item == "Religion":
            print("p")
            return f"1d20+{self.religion_mod}"
        elif item == "Society":
            print("q")
            return f"1d20+{self.society_mod}"
        elif item == "Stealth":
            print("r")
            return f"1d20+{self.stealth_mod}"
        elif item == "Survival":
            print("s")
            return f"1d20+{self.survival_mod}"
        elif item == "Thievery":
            print("t")
            return f"1d20+{self.thievery_mod}"
        else:
            print("Not a check")
            try:
                print(f"{item} - attk")
                return await self.weapon_attack(item)
            except KeyError:
                pass

            for attack in self.character_model.spells:
                print(f"{item} - spell")
                # print(attack["name"])
                if attack["name"] in item:
                    stat_mod = 0
                    match attack["ability"]:  # noqa
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

    async def weapon_attack(self, item):
        logging.info("weapon_attack")
        weapon = self.character_model.attacks[item]
        # print(weapon)
        # print(item)
        # print(weapon["display"])
        attk_stat = self.str_mod
        # print(f"Saved attack stat: {weapon['attk_stat']}")
        match weapon["attk_stat"]:
            case "dex":
                attk_stat = self.dex_mod
            case "con":
                attk_stat = self.con_mod
            case "itl":
                attk_stat = self.itl_mod
            case "wis":
                attk_stat = self.wis_mod
            case "cha":
                attk_stat = self.cha_mod
            case "None":
                attk_stat = 0
        proficiency = 0
        if "override_prof" in weapon.keys():
            proficiency = weapon["override_prof"]
        else:
            match weapon["prof"]:
                case "unarmed":
                    proficiency = self.character_model.unarmed_prof
                case "simple":
                    proficiency = self.character_model.simple_prof
                case "martial":
                    proficiency = self.character_model.martial_prof
                case "advanced":
                    proficiency = self.character_model.advanced_prof
        # print(f"proficiency: {proficiency}")
        # print(f"attack stat: {attk_stat}")
        # print(self.character_model.level)
        # print(f"potency {weapon['pot']}")
        if weapon["prof"] == "NPC":
            attack_mod = attk_stat + self.character_model.level + weapon["pot"]
        elif proficiency > 0:
            attack_mod = attk_stat + self.character_model.level + proficiency + weapon["pot"]
        else:
            attack_mod = attk_stat

        bonus_mod = await bonus_calc(0, "attack", self.character_model.bonuses)
        # print(attack_mod)
        return f"1d20+{attack_mod}{ParseModifiers(f'{bonus_mod}')}"

    async def weapon_dmg(self, item, crit: bool = False):
        weapon = self.character_model.attacks[item]
        bonus_mod = await bonus_calc(0, "dmg", self.character_model.bonuses)
        dmg_mod = 0
        match weapon["stat"]:
            case None:
                dmg_mod = 0
            case "None":
                dmg_mod = 0
            case "str":
                dmg_mod = self.str_mod
            case "dex":
                dmg_mod = self.dex_mod
            case "con":
                dmg_mod = self.con_mod
            case "itl":
                dmg_mod = self.itl_mod
            case "wis":
                dmg_mod = self.wis_mod
            case "cha":
                dmg_mod = self.cha_mod
            case _:
                dmg_mod = weapon["stat"]

        die = weapon["die"]
        if die[0] != "d":
            die = f"d{die}"

        # Special Trait categories
        for item in weapon["traits"]:
            if item.strip().lower() == "propulsive":
                if self.str_mod > 0:
                    dmg_mod += floor(self.str_mod / 2)
                else:
                    dmg_mod += self.str_mod
            if "fatal" in item.strip().lower():
                parsed_string = item.split("-")
                die = parsed_string[1]
                weapon["crit"] = f"*2+{parsed_string[1]}"

        if crit:
            return f"({weapon['die_num']}{die}+{dmg_mod}{ParseModifiers(f'{bonus_mod}')}){weapon['crit']}"
        else:
            return f"{weapon['die_num']}{die}+{dmg_mod}{ParseModifiers(f'{bonus_mod}')}"

    async def get_weapon(self, item):
        return self.character_model.attacks[item]

    async def get_spell_mod(self, spell, mod: bool):
        """
        Returns the spell modifier for the spell
        :param spell str:
        :param mod bool: True = Modifier, False = DC
        :return: Spell_Modifier integer
        """

        spell_data = self.character_model.spells[spell]

        attk_stat = self.str_mod
        match spell_data["ability"]:
            case "dex":
                attk_stat = self.dex_mod
            case "con":
                attk_stat = self.con_mod
            case "int":
                attk_stat = self.itl_mod
            case "wis":
                attk_stat = self.wis_mod
            case "cha":
                attk_stat = self.cha_mod
            case "None":
                attk_stat = 0

        if spell_data["tradition"] == "NPC":
            if mod:
                return attk_stat + self.character_model.level + spell_data["proficiency"]
            else:
                return attk_stat + self.character_model.level + spell_data["dc"]
        else:
            if mod:
                return attk_stat + self.character_model.level + spell_data["proficiency"]
            else:
                return 10 + attk_stat + self.character_model.level + spell_data["proficiency"]

    async def get_spell_dmg(self, spell: str, level: int):
        print(self.character_model.spells)
        spell_data = self.character_model.spells[spell]
        dmg_string = ""
        for x, key in enumerate(spell_data["damage"]):
            if x > 0:
                dmg_string += "+"
            if spell_data["damage"][key]["mod"]:
                mod_stat = self.str_mod
                match spell_data["ability"]:
                    case "dex":
                        mod_stat = self.dex_mod
                    case "con":
                        mod_stat = self.con_mod
                    case "int":
                        mod_stat = self.itl_mod
                    case "wis":
                        mod_stat = self.wis_mod
                    case "cha":
                        mod_stat = self.cha_mod
                    case "None":
                        mod_stat = 0

                dmg_string += f"{spell_data['damage'][key]['value']}+{mod_stat}"
            else:
                dmg_string += f"{spell_data['damage'][key]['value']}"

            # Heightening Calculations
        if level > spell_data["level"] and spell_data["heightening"]["type"] == "interval":
            print(level)
            print(spell_data["level"])
            if spell_data["level"] == 0:
                base_level = 1
            else:
                base_level = spell_data["level"]
            differance = level - base_level
            print(differance)
            steps = floor(differance / spell_data["heightening"]["interval"])
            print(steps)
            for i in range(0, steps):
                print(i)
                print(spell_data["heightening"]["damage"])
                for x, key in enumerate(spell_data["heightening"]["damage"]):
                    print(x, key)
                    if x > 0:
                        dmg_string += "+"
                    dmg_string = f"{dmg_string}+{spell_data['heightening']['damage'][key]}"
        # Add fixed calcs
        elif level > spell_data["level"] and spell_data["heightening"]["type"] == "fixed":
            if level in spell_data["heightening"]["interval"].keys():
                for item in spell_data["heightening"]["interval"]["value"].keys():
                    if item["applyMod"]:
                        mod_stat = self.str_mod
                        match spell_data["ability"]:
                            case "dex":
                                mod_stat = self.dex_mod
                            case "con":
                                mod_stat = self.con_mod
                            case "int":
                                mod_stat = self.itl_mod
                            case "wis":
                                mod_stat = self.wis_mod
                            case "cha":
                                mod_stat = self.cha_mod
                            case "None":
                                mod_stat = 0
                        extra_dmg = f"{item['value']}+{mod_stat}"
                    else:
                        extra_dmg = f"{item['value']}"
                    dmg_string = f"{dmg_string}+{extra_dmg}"

        return dmg_string

    async def get_spell_dmg_type(self, spell):
        spell_data = self.character_model.spells[spell]
        for key in spell_data["damage"].keys():
            return spell_data["damage"][key]["dmg_type"].lower()

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

    async def roll_macro(self, macro, modifier):
        macro_string = await self.get_roll(macro)
        if macro_string == 0:
            return 0
        roll_string = f"{macro_string}{ParseModifiers(modifier)}"
        # print(roll_string)
        dice_result = d20.roll(roll_string)
        return dice_result

    async def macro_list(self):
        list = self.character_model.macros.split(",")
        logging.info(list)
        if len(list) > 0:
            if list[-1] == "":
                return list[:-1]
            else:
                return list
        else:
            return []

    async def attack_list(self):
        list = []
        for key in self.character_model.attacks:
            list.append(key)
        return list

    async def set_cc(
        self,
        title: str,
        counter: bool,
        number: int,
        unit: str,
        auto_decrement: bool,
        flex: bool = False,
        data: str = "",
        visible: bool = True,
    ):
        logging.info("set_cc")
        # Get the Character's data

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)

        # Check to make sure there isn't a condition with the same name on the character
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == self.id).where(Condition.title == title)
            )
            check_con = result.scalars().all()
            if len(check_con) > 0:
                return False

        # Process Data
        # print(data)
        if data == "":
            # print(title)
            if title in EPF_Conditions:
                data = EPF_Conditions[title]
                # print(data)

        # Write the condition to the table
        try:
            if not self.guild.timekeeping or unit == "Round":  # If its not time based, then just write it
                async with session.begin():
                    condition = Condition(
                        character_id=self.id,
                        title=title,
                        number=number,
                        counter=counter,
                        auto_increment=auto_decrement,
                        time=False,
                        flex=flex,
                        action=data,
                        visible=visible,
                    )
                    session.add(condition)
                await session.commit()
                # await update_pinned_tracker(ctx, engine, bot)
                return True

            else:  # If its time based, then calculate the end time, before writing it
                current_time = await get_time(self.ctx, self.engine)
                if unit == "Minute":
                    end_time = current_time + datetime.timedelta(minutes=number)
                elif unit == "Hour":
                    end_time = current_time + datetime.timedelta(hours=number)
                else:
                    end_time = current_time + datetime.timedelta(days=number)

                timestamp = end_time.timestamp()

                async with session.begin():
                    condition = Condition(
                        character_id=self.id,
                        title=title,
                        number=timestamp,
                        counter=counter,
                        auto_increment=True,
                        time=True,
                        action=data,
                        visible=visible,
                    )
                    session.add(condition)
                await session.commit()
                # await update_pinned_tracker(ctx, engine, bot)
            await self.update()
            return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"set_cc: {e}")
            return False

    # Delete CC
    async def delete_cc(self, condition):
        result = await super().delete_cc(condition)
        await self.update()
        return result

    async def update_resistance(self, weak, item, amount):
        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
        try:
            updated_resistance = self.resistance
            # print(updated_resistance)
            if amount == 0:
                async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                async with async_session() as session:
                    query = await session.execute(select(Condition).where(func.lower(Condition.item) == item.lower()))
                    condition_object = query.scalars().one()
                    await session.delete(condition_object)
                    await session.commit()
                return True
            else:
                condition_string = f"{item} {weak} {amount};"
                result = await self.set_cc(item, True, amount, "Round", False, data=condition_string, visible=False)

            await self.update()
            # print(self.resistance)
            return True
        except Exception:
            return False

    async def show_resistance(self):
        embeds = []

        resists = ""
        for key, value in self.resistance["resist"].items():
            resists += f"{key.title()}: {value}\n"
        resist_embed = discord.Embed(
            title="Resistances",
            description=resists,
        )
        embeds.append(resist_embed)

        weak = ""
        for key, value in self.resistance["weak"].items():
            weak += f"{key.title()}: {value}\n"
        weak_embed = discord.Embed(
            title="Weaknesses",
            description=weak,
        )
        embeds.append(weak_embed)

        immune = ""
        for key, value in self.resistance["immune"].items():
            immune += f"{key.title()}\n"
        immune_embed = discord.Embed(
            title="Immunities",
            description=immune,
        )
        embeds.append(immune_embed)
        return embeds

    async def change_hp(self, amount: int, heal: bool, post=True):
        if self.character_model.eidolon:
            Partner = await get_EPF_Character(
                self.character_model.partner, self.ctx, engine=self.engine, guild=self.guild
            )
            await Partner.change_hp(amount, heal, post)
            await self.set_hp(Partner.current_hp)
            return True
        else:
            await super().change_hp(amount, heal, post)
            if self.character_model.partner is not None:
                Eidolon = await get_EPF_Character(
                    self.character_model.partner, self.ctx, engine=self.engine, guild=self.guild
                )
                await Eidolon.set_hp(self.current_hp)
            return True

    # Set the initiative
    async def set_init(self, init):
        logging.info(f"set_init {self.char_name} {init}")
        if self.ctx is None and self.guild is None:
            raise LookupError("No guild reference")

        if type(init) == str:
            if init.lower() in EPF_SKills_NO_SAVE:
                init = await self.get_roll(init)
            roll = d20.roll(init)
            init = roll.total
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            if self.guild is None:
                Tracker = await get_EPF_tracker(
                    self.ctx,
                    self.engine,
                )
            else:
                Tracker = await get_EPF_tracker(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.char_name))
                character = char_result.scalars().one()
                character.init = init
                await session.commit()
            await self.update()
            return f"Initiative set to {init} for {self.char_name}"
        except Exception as e:
            logging.error(f"set_init: {e}")
            return f"Failed to set initiative: {e}"

    async def get_char_sheet(self, bot):
        try:
            if self.character_model.player:
                status = "PC:"
            else:
                status = "NPC:"

            condition_list = await self.conditions()
            user_name = bot.get_user(self.user).name

            embed = discord.Embed(
                title=f"{self.char_name}",
                fields=[
                    discord.EmbedField(name="Name: ", value=self.char_name, inline=False),
                    discord.EmbedField(name=status, value=user_name, inline=False),
                    discord.EmbedField(
                        name="HP: ",
                        value=f"{self.current_hp}/{self.max_hp}: ({self.temp_hp} Temp)",
                        inline=False,
                    ),
                    discord.EmbedField(name="Class: ", value=self.character_model.char_class, inline=False),
                ],
                color=discord.Color.dark_gold(),
            )
            # if condition_list != None:
            condition_embed = discord.Embed(
                title="Conditions",
                fields=[],
                color=discord.Color.dark_teal(),
            )
            counter_embed = discord.Embed(
                title="Counters",
                fields=[],
                color=discord.Color.dark_magenta(),
            )
            for item in condition_list:
                await asyncio.sleep(0)
                if not item.visible:
                    embed.fields.append(discord.EmbedField(name=item.title, value=item.number, inline=True))
                elif item.visible and not item.time:
                    if not item.counter:
                        condition_embed.fields.append(discord.EmbedField(name=item.title, value=item.number))
                    elif item.counter:
                        if item.number != 0:
                            counter_embed.fields.append(discord.EmbedField(name=item.title, value=item.number))
                        else:
                            counter_embed.fields.append(discord.EmbedField(name=item.title, value="_"))
                elif item.visible and item.time and not item.counter:
                    condition_embed.fields.append(
                        discord.EmbedField(
                            name=item.title,
                            value=await time_keeping_functions.time_left(self.ctx, self.engine, bot, item.number),
                        )
                    )
            output = [embed, counter_embed, condition_embed]
            output.extend(await self.show_resistance())
            return output
        except NoResultFound:
            await self.ctx.respond(error_not_initialized, ephemeral=True)
            return False
        except IndexError:
            await self.ctx.respond("Ensure that you have added characters to the initiative list.")
        except Exception:
            await self.ctx.respond("Failed")


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

    try:
        guild = await get_guild(ctx, guild)
        EPF_tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        initiative_num = 0
        if guild.initiative is not None:
            print("In initiative")
            try:
                perception = (
                    int(pb["build"]["proficiencies"]["perception"])
                    + pb["build"]["level"]
                    + floor((pb["build"]["abilities"]["wis"] - 10) / 2)
                )
                roll = d20.roll(f"1d20+{perception}")
                initiative_num = roll.total
            except Exception:
                initiative_num = 0

        print(initiative_num)
        # Check to see if character already exists, if it does, update instead of creating

        async with async_session() as session:
            query = await session.execute(select(EPF_tracker).where(EPF_tracker.name == char_name))
            character = query.scalars().all()
        if len(character) > 0:
            overwrite = True
            character = character[0]

        lores = ""
        for item, value in pb["build"]["lores"]:
            output = f"{item}, {value}; "
            lores += output

        feats = ""
        for item in pb["build"]["feats"]:
            feats += f"{item[0]}, "

        if overwrite:
            attacks = character.attacks
            name_list = []
            for item in pb["build"]["weapons"]:
                name_list.append(item["display"])
            for key in attacks:
                if key not in name_list:
                    del attacks[key]
            for item in pb["build"]["weapons"]:
                die_num = 0
                match item["str"]:
                    case "":
                        die_num = 1
                    case "striking":
                        die_num = 2
                    case "greaterStriking":
                        die_num = 3
                    case "majorStriking":
                        die_num = 4

                attacks[item["display"]] = {
                    "display": item["display"],
                    "prof": item["prof"],
                    "die": item["die"],
                    "pot": item["pot"],
                    "str": item["str"],
                    "die_num": die_num,
                    "name": item["name"],
                    "runes": item["runes"],
                }
        else:
            attacks = {}
            for item in pb["build"]["weapons"]:
                die_num = 0
                match item["str"]:
                    case "":
                        die_num = 1
                    case "striking":
                        die_num = 2
                    case "greaterStriking":
                        die_num = 3
                    case "majorStriking":
                        die_num = 4
                attacks[item["display"]] = {
                    "display": item["display"],
                    "prof": item["prof"],
                    "die": item["die"],
                    "pot": item["pot"],
                    "str": item["str"],
                    "name": item["name"],
                    "runes": item["runes"],
                    "die_num": die_num,
                    "crit": "*2",
                    "stat": "str",
                    "dmg_type": "Bludgeoning",
                    "attk_stat": "str",
                }
                edited_attack = await attack_lookup(attacks[item["display"]], pb)
                attacks[item["display"]] = edited_attack

        print(attacks)

        # Spells
        spells_raw = pb["build"]["spellCasters"]
        spell_library = {}
        for item in spells_raw:
            for spell_level in item["spells"]:
                for spell_name in spell_level["list"]:
                    spell_data = await spell_lookup(spell_name)
                    if spell_data[0] is True:
                        spell = {
                            "level": spell_level["spellLevel"],
                            "tradition": item["magicTradition"],
                            "ability": item["ability"],
                            "proficiency": item["proficiency"],
                            "type": spell_data[1].type,
                            "save": spell_data[1].save,
                            "damage": spell_data[1].damage,
                            "heightening": spell_data[1].heightening,
                        }
                        spell_library[spell_name] = spell

        if overwrite:
            async with async_session() as session:
                query = await session.execute(select(EPF_tracker).where(EPF_tracker.name == char_name))
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
                character.ac_base = pb["build"]["acTotal"]["acTotal"]
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
                character.attacks = attacks
                character.spells = spell_library
                await session.commit()

        else:  # Create a new character
            async with async_session() as session:
                async with session.begin():
                    new_char = EPF_tracker(
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
                        ac_base=pb["build"]["acTotal"]["acTotal"],
                        init=initiative_num,
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
                        attacks=attacks,
                        spells=spell_library,
                        resistance={"resist": {}, "weak": {}, "immune": {}},
                    )
                    session.add(new_char)
                await session.commit()

        await delete_intested_items(char_name, ctx, guild, engine)
        for item in pb["build"]["equipment"]:
            print(item)
            result = await invest_items(item[0], char_name, ctx, guild, engine)
            print(result)

        Character = await get_EPF_Character(char_name, ctx, guild, engine)
        await Character.update()
        return True
    except Exception:
        return False


async def calculate(ctx, engine, char_name, guild=None):
    logging.info("Updating Character Model")
    guild = await get_guild(ctx, guild=guild)
    # Database boilerplate
    if guild is not None:
        PF2_tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
    else:
        PF2_tracker = await get_EPF_tracker(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    # print(char_name)
    bonuses, resistance = await parse_bonuses(ctx, engine, char_name, guild=guild)
    # print(bonuses)

    async with async_session() as session:
        try:
            query = await session.execute(select(PF2_tracker).where(PF2_tracker.name == char_name))
            character = query.scalars().one()
            if "Untrained Improvisation" in character.feats:
                ui = True
            else:
                ui = False

            # Go through each of the items.

            # Stat Mods - Do this first, because they are used in later calculations
            character.str_mod = await ability_mod_calc(character.str, "str", bonuses)
            character.dex_mod = await ability_mod_calc(character.dex, "dex", bonuses)
            character.con_mod = await ability_mod_calc(character.con, "con", bonuses)
            character.itl_mod = await ability_mod_calc(character.itl, "itl", bonuses)
            character.wis_mod = await ability_mod_calc(character.wis, "wis", bonuses)
            character.cha_mod = await ability_mod_calc(character.cha, "cha", bonuses)

            # Saves
            character.fort_mod = await save_mod_calc(
                character.con_mod, "fort", character.fort_prof, character.level, bonuses
            )
            character.reflex_mod = await save_mod_calc(
                character.dex_mod, "reflex", character.reflex_prof, character.level, bonuses
            )
            character.will_mod = await save_mod_calc(
                character.wis_mod, "wis", character.will_prof, character.level, bonuses
            )

            # Skills
            character.athletics_mod = await skill_mod_calc(
                character.str_mod, "athletics", character.athletics_prof, character.level, bonuses, ui
            )
            character.acrobatics_mod = await skill_mod_calc(
                character.dex_mod, "acrobatics", character.acrobatics_prof, character.level, bonuses, ui
            )
            character.arcana_mod = await skill_mod_calc(
                character.itl_mod, "arcana", character.arcana_prof, character.level, bonuses, ui
            )
            character.crafting_mod = await skill_mod_calc(
                character.itl_mod, "crafting", character.acrobatics_prof, character.level, bonuses, ui
            )
            character.deception_mod = await skill_mod_calc(
                character.cha_mod, "deception", character.deception_prof, character.level, bonuses, ui
            )
            character.diplomacy_mod = await skill_mod_calc(
                character.cha_mod, "diplomacy", character.diplomacy_prof, character.level, bonuses, ui
            )
            character.intimidation_mod = await skill_mod_calc(
                character.cha_mod, "intimidation", character.intimidation_prof, character.level, bonuses, ui
            )
            character.medicine_mod = await skill_mod_calc(
                character.wis_mod, "medicine", character.medicine_prof, character.level, bonuses, ui
            )
            character.nature_mod = await skill_mod_calc(
                character.wis_mod, "nature", character.nature_prof, character.level, bonuses, ui
            )
            character.occultism_mod = await skill_mod_calc(
                character.itl_mod, "occultism", character.occultism_prof, character.level, bonuses, ui
            )
            character.perception_mod = await skill_mod_calc(
                character.wis_mod, "perception", character.perception_prof, character.level, bonuses, ui
            )
            character.performance_mod = await skill_mod_calc(
                character.cha_mod, "performance", character.performance_prof, character.level, bonuses, ui
            )
            character.religion_mod = await skill_mod_calc(
                character.wis_mod, "religion", character.religion_prof, character.level, bonuses, ui
            )
            character.society_mod = await skill_mod_calc(
                character.itl_mod, "society", character.society_prof, character.level, bonuses, ui
            )
            character.stealth_mod = await skill_mod_calc(
                character.dex_mod, "stealth", character.stealth_prof, character.level, bonuses, ui
            )
            character.survival_mod = await skill_mod_calc(
                character.wis_mod, "survival", character.survival_prof, character.level, bonuses, ui
            )
            character.thievery_mod = await skill_mod_calc(
                character.dex_mod, "thievery", character.thievery_prof, character.level, bonuses, ui
            )

            # Casting, Armor and Attacks
            key_ability = 0

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

            character.arcane_mod = await skill_mod_calc(
                key_ability, "arcane", character.arcane_prof, character.level, bonuses, False
            )
            character.divine_mod = await skill_mod_calc(
                key_ability, "divine", character.divine_prof, character.level, bonuses, False
            )
            character.occult_mod = await skill_mod_calc(
                key_ability, "occult", character.arcane_prof, character.level, bonuses, False
            )
            character.primal_mod = await skill_mod_calc(
                key_ability, "primal", character.arcane_prof, character.level, bonuses, False
            )

            character.ac_total = await bonus_calc(character.ac_base, "ac", bonuses)
            character.class_dc = await skill_mod_calc(
                key_ability, "class_dc", character.class_prof, character.level, bonuses, False
            )
            character.init_string = f"1d20+{character.perception_mod}"
            character.bonuses = bonuses
            character.resistance = resistance

            macros = []
            for item in character.attacks.keys():
                # print(item)
                macros.append(item)
            # for item in character.spells.keys():
            #     macros.append(f"Spell Attack: {item['name']}")
            macros.extend(PF2_skills)

            Macro = await get_macro(ctx, engine, id=guild.id)
            async with async_session() as macro_session:
                result = await macro_session.execute(select(Macro.name).where(Macro.character_id == character.id))
                macro_list = result.scalars().all()
            macros.extend(macro_list)

            macro_string = ""
            for item in macros:
                macro_string += f"{item},"
            character.macros = macro_string

            await session.commit()

        except Exception as e:
            logging.warning(f"pf2 - enchanced character importer: {e}")


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


async def skill_mod_calc(stat_mod, skill: str, skill_prof, level, bonuses, ui):
    # TODO Throw in code for Untrained improvisation
    if skill_prof == 0 and not ui:
        mod = stat_mod
    elif skill_prof == 0 and ui:
        if level < 7:
            mod = stat_mod + math.floor(level / 2)
        else:
            mod = stat_mod + level
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
    # print(f"{skill}, {stat_mod} {skill_prof} {level}: {mod}")
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


async def parse_bonuses(ctx, engine, char_name: str, guild=None):
    guild = await get_guild(ctx, guild=guild)
    # Database boilerplate
    if guild is not None:
        PF2_tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
    else:
        PF2_tracker = await get_EPF_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with async_session() as session:
            result = await session.execute(select(PF2_tracker.id).where(PF2_tracker.name == char_name))
            char = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(select(Condition).where(Condition.character_id == char))
            conditions = result.scalars().all()
    except NoResultFound:
        conditions = []

    bonuses = {
        "circumstances_pos": {},
        "status_pos": {},
        "item_pos": {},
        "circumstances_neg": {},
        "status_neg": {},
        "item_neg": {},
    }
    resistances = {"resist": {}, "weak": {}, "immune": {}}

    # print("!!!!!!!!!!!!!!!!!!!111")
    # print(len(conditions))
    for condition in conditions:
        # print(f"{condition.title}, {condition.number}, {condition.action}")
        await asyncio.sleep(0)
        # Get the data from the conditions
        # Write the bonuses into the two dictionaries
        print(f"{condition.title}, {condition.action}")

        data: str = condition.action
        data_list = data.split(",")
        for item in data_list:
            try:
                parsed = item.strip().split(" ")
                if parsed[0].title() in EPF.EPF_Support.EPF_DMG_Types_Inclusive:
                    print(True)
                    print("Condition")
                    print(f"0: {parsed[0]}, 1: {parsed[1]}, 2: {parsed[2]}")
                    if parsed[2][-1] == ";":
                        parsed[2] = parsed[2][:-1]
                    parsed[0] = parsed[0].lower()
                    match parsed[1]:
                        case "r":
                            resistances["resist"][parsed[0]] = int(parsed[2])
                        case "w":
                            resistances["weak"][parsed[0]] = int(parsed[2])
                        case "i":
                            resistances["immune"][parsed[0]] = 1
                else:
                    for dmg in EPF.EPF_Support.EPF_DMG_Types:
                        print(parsed[0].title(), dmg)
                        if dmg == parsed[0]:
                            print("Match")
                        else:
                            print(type(parsed[0]), type(dmg))

                key = parsed[0]
                if parsed[1][1:] == "X":
                    value = int(condition.number)
                else:
                    try:
                        value = int(parsed[1][1:])
                    except ValueError:
                        value = int(parsed[1])

                if parsed[2] == "s" and parsed[1][0] == "+":  # Status Positive
                    if key in bonuses["status_pos"]:
                        if value > bonuses["status_pos"][key]:
                            bonuses["status_pos"][key] = value
                    else:
                        bonuses["status_pos"][key] = value
                elif parsed[2] == "s" and parsed[1][0] == "-":  # Status Negative
                    if key in bonuses["status_neg"]:
                        if value > bonuses["status_neg"][key]:
                            bonuses["status_neg"][key] = value
                    else:
                        bonuses["status_neg"][key] = value
                        # print(f"{key}: {bonuses['status_neg'][key]}")
                elif parsed[2] == "c" and parsed[1][0] == "+":  # Circumstances Positive
                    if key in bonuses["circumstances_pos"]:
                        if value > bonuses["circumstances_pos"][key]:
                            bonuses["circumstances_pos"][key] = value
                    else:
                        bonuses["circumstances_pos"][key] = value
                elif parsed[2] == "c" and parsed[1][0] == "-":  # Circumstances Positive
                    if key in bonuses["circumstances_neg"]:
                        if value > bonuses["circumstances_neg"][key]:
                            bonuses["circumstances_neg"][key] = value
                    else:
                        bonuses["circumstances_neg"][key] = value
                        # print(f"{key}: {bonuses['circumstances_neg'][key]}")
                elif parsed[2] == "i" and parsed[1][0] == "+":  # Item Positive
                    if key in bonuses["item_pos"]:
                        if value > bonuses["item_pos"][key]:
                            bonuses["item_pos"][key] = value
                    else:
                        bonuses["item_pos"][key] = value
                        # print(f"{key}: {bonuses['item_pos'][key]}")
                elif parsed[2] == "i" and parsed[1][0] == "-":  # Item Negative
                    if key in bonuses["item_neg"]:
                        if value > bonuses["item_neg"][key]:
                            bonuses["item_neg"][key] = value
                    else:
                        bonuses["item_neg"][key] = value

            except Exception:
                pass

    # print(bonuses)
    print(resistances)
    return bonuses, resistances


class EPF_Weapon(Base):
    __tablename__ = "EPF_item_data"
    # Columns
    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(), unique=True)
    level = Column(Integer())
    base_item = Column(String(), unique=False)
    category = Column(String(), unique=False)
    damage_type = Column(String(), unique=False)
    damage_dice = Column(Integer())
    damage_die = Column(String(), unique=False)
    group = Column(String(), unique=False)
    range = Column(Integer())
    potency_rune = Column(Integer())
    striking_rune = Column(String(), unique=False)
    runes = Column(String())
    traits = Column(JSON())


class EPF_Equipment(Base):
    __tablename__ = "EPF_equipment_data"
    # Columns
    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(), unique=True)
    level = Column(Integer())
    data = Column(JSON())


class EPF_Spells(Base):
    __tablename__ = "EPF_spell_data"
    # Columns
    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(), unique=True)
    level = Column(Integer())
    type = Column(String())
    save = Column(JSON())
    traditions = Column(JSON())
    school = Column(String())
    damage = Column(JSON())
    heightening = Column(JSON())


async def attack_lookup(attack, pathbuilder):
    lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    async_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
    print(attack["display"])
    try:
        display_name = attack["display"].strip()
        async with async_session() as session:
            result = await session.execute(
                select(EPF_Weapon).where(func.lower(EPF_Weapon.name) == display_name.lower())
            )
            data = result.scalars().one()
    except Exception:
        item_name = attack["name"].strip()
        async with async_session() as session:
            result = await session.execute(select(EPF_Weapon).where(func.lower(EPF_Weapon.name) == item_name.lower()))
            data = result.scalars().one()
    print(data.name, data.range, data.traits)
    await lookup_engine.dispose()

    if data.range is not None:
        attack["stat"] = None
        attack["attk_stat"] = "dex"
    # print(data.name)
    # print(data.traits)
    for item in data.traits:
        if "deadly" in item:
            if "deadly" in item:
                string = item.split("-")
                if data.striking_rune == "greaterStriking":
                    dd = 2
                elif data.striking_rune == "majorStriking":
                    dd = 3
                else:
                    dd = 1
                attack["crit"] = f"*2 + {dd}{string[1]}"
        elif (
            item.strip().lower() == "finesse"
            and pathbuilder["build"]["abilities"]["dex"] > pathbuilder["build"]["abilities"]["str"]
        ):
            # print("Finesse")
            attack["attk_stat"] = "dex"
        elif item.strip().lower() == "brutal":
            attack["attk_stat"] = "str"
    attack["traits"] = data.traits
    attack["dmg_type"] = data.damage_type
    print(attack)
    return attack


async def delete_intested_items(character, ctx, guild, engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    EPF_Tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    async with async_session() as session:
        char_result = await session.execute(select(EPF_Tracker.id).where(EPF_Tracker.name == character))
        id = char_result.scalars().one()
    async with async_session() as session:
        results = await session.execute(
            select(Condition).where(Condition.visible == false()).where(Condition.counter == true())
        )
        condition_list = results.scalars().all()

    for con in condition_list:
        await asyncio.sleep(0)
        async with async_session() as session:
            await session.delete(con)
            await session.commit()


async def invest_items(item, character, ctx, guild, engine):
    lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    lookup_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
    write_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    condition_string = ""
    try:
        item = item.strip()
        async with lookup_session() as lookup_session:
            result = await lookup_session.execute(
                select(EPF_Equipment.data).where(func.lower(EPF_Equipment.name) == item.lower())
            )
            data = result.scalars().all()
            if len(data) > 0:
                data = data[0]
                print(data)
                for key in data.keys():
                    if key in EPF_SKills:
                        if data[key]["mode"] == "item":
                            condition_string += f"{key} {ParseModifiers(str(data[key]['bonus']))} i, "
        await lookup_engine.dispose()
        if condition_string != "":
            print(condition_string)
            EPF_Tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
            Condition = await get_condition(ctx, engine, id=guild.id)
            async with write_session() as write_session:
                char_result = await write_session.execute(select(EPF_Tracker.id).where(EPF_Tracker.name == character))
                id = char_result.scalars().one()

            async with write_session.begin():
                write_session.add(
                    Condition(
                        character_id=id,
                        title=f"{item}",
                        number=0,
                        counter=True,
                        visible=False,
                        action=(condition_string),
                    )
                )
                await write_session.commit()
                print("Committed")
            return True
        else:
            return False
    except Exception:
        await engine.dispose()
        return False


async def spell_lookup(spell: str):
    """
    :param spell: string
    :return: tuple of Success (Boolean), Data (dict)
    """
    lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    lookup_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
    try:
        spell = spell.strip()
        async with lookup_session() as lookup_session:
            result = await lookup_session.execute(
                select(EPF_Spells).where(func.lower(EPF_Spells.name) == spell.lower())
            )
            spell_data = result.scalars().one()
        return True, spell_data
    except Exception:
        return False, {}
