# pf2_functions.py
import asyncio
import datetime
import logging
import math
from math import floor
import lark
from lark import Lark

import aiohttp
import d20
import discord
from sqlalchemy import select
from sqlalchemy import true, Column, Integer, String, JSON, false, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import EPF.EPF_Support
import time_keeping_functions
from Base.Character import Character
from EPF.EPF_Support import EPF_Conditions, EPF_SKills, EPF_SKills_NO_SAVE
from database_models import (
    get_condition,
    get_EPF_tracker,
    Base,
    LookupBase,
    get_macro,
    get_tracker,
)
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA, engine
from database_operations import get_asyncio_db_engine, DATABASE
from error_handling_reporting import error_not_initialized
from time_keeping_functions import get_time
from utils.parsing import ParseModifiers
from utils.utils import get_guild

from EPF.Kineticist_DB import Kineticist_DB
from EPF.EPF_Automation_Data import EPF_retreive_complex_data

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

default_pic = (
    "https://cdn.discordapp.com/attachments/1028702442927431720/1107574256763687012/"
    "artica_A_portrait_of_a_generic_fantasy_character._Cloaked_in_sh_4c0a4013-2c63-4a11-9754-66acba4c7319.png"
)


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
            result = await session.execute(select(EPF_tracker).where(func.lower(EPF_tracker.name) == char_name.lower()))
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
        self.class_dc = character.class_dc

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
        self.pic = character.pic if character.pic is not None else default_pic

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
        print("UPDATING!!!!!!!!!!!")

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
        self.class_dc = self.character_model.class_dc

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
        self.pic = self.character_model.pic if self.character_model.pic is not None else default_pic

    async def get_roll(self, item: str):
        logging.info(f"Returning roll: {item}")
        # print(item)
        if item == "Fortitude" or item == "Fort" or item == "fort":
            # print("a")
            return f"1d20+{self.fort_mod}"
        elif item == "Reflex" or item == "reflex":
            # print("b")
            return f"1d20+{self.reflex_mod}"
        elif item == "Will" or item == "reflex":
            # print("c")
            return f"1d20+{self.will_mod}"
        elif item == "class_dc":
            return f"1d20+{self.class_dc}"
        elif item == "Acrobatics":
            # print("d")
            return f"1d20+{self.acrobatics_mod}"
        elif item == "Arcana":
            # print("e")
            return f"1d20+{self.arcana_mod}"
        elif item == "Athletics":
            # print("f")
            return f"1d20+{self.athletics_mod}"
        elif item == "Crafting":
            # print("g")
            return f"1d20+{self.crafting_mod}"
        elif item == "Deception":
            # print("h")
            return f"1d20+{self.deception_mod}"
        elif item == "Diplomacy":
            # print("i")
            return f"1d20+{self.diplomacy_mod}"
        elif item == "Intimidation":
            # print("j")
            return f"1d20+{self.intimidation_mod}"
        elif item == "Medicine":
            # print("k")
            return f"1d20+{self.medicine_mod}"
        elif item == "Nature":
            # print("l")
            return f"1d20+{self.nature_mod}"
        elif item == "Occultism":
            # print("m")
            return f"1d20+{self.occultism_mod}"
        elif item == "Perception":
            # print("n")
            return f"1d20+{self.perception_mod}"
        elif item == "Performance":
            # print("o")
            return f"1d20+{self.performance_mod}"
        elif item == "Religion":
            # print("p")
            return f"1d20+{self.religion_mod}"
        elif item == "Society":
            # print("q")
            return f"1d20+{self.society_mod}"
        elif item == "Stealth":
            # print("r")
            return f"1d20+{self.stealth_mod}"
        elif item == "Survival":
            # print("s")
            return f"1d20+{self.survival_mod}"
        elif item == "Thievery":
            # print("t")
            return f"1d20+{self.thievery_mod}"
        elif "Lore" in item:
            lore = item.split(":")[1]
            lore = lore.strip()
            lore_list = self.character_model.lores.split(";")
            for i in lore_list:
                parsed_lore = i.split(",")
                if lore == parsed_lore[0].strip():
                    if "Untrained Improvisation" in self.character_model.feats:
                        ui = True
                    else:
                        ui = False
                    # print(f"Int Mod: {self.itl_mod}, Prof: {parsed_lore[1]}, Level: {self.character_model.level}")

                    return (
                        f"1d20+{await skill_mod_calc(self.itl_mod, 'lore', int(parsed_lore[1]), self.character_model.level, self.character_model.bonuses, ui)} "
                    )

        else:
            try:
                return await self.weapon_attack(item)
            except KeyError:
                pass
            try:
                for attack in self.character_model.spells:
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
            except TypeError:
                pass

            return 0

    async def weapon_attack(self, item):
        logging.info("weapon_attack")
        weapon = self.character_model.attacks[item]

        attk_stat = self.str_mod
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

        if weapon["prof"] == "NPC":
            attack_mod = attk_stat + self.character_model.level + weapon["pot"]
        elif weapon["prof"] == "NPC_C":
            attack_mod = weapon["pot"]
        elif proficiency > 0:
            attack_mod = attk_stat + self.character_model.level + proficiency + weapon["pot"]
        else:
            attack_mod = attk_stat

        bonus_mod = await bonus_calc(0, "attack", self.character_model.bonuses, item_name=item)

        return f"1d20+{attack_mod}{ParseModifiers(f'{bonus_mod}')}"

    async def weapon_dmg(self, item, crit: bool = False, flat_bonus: str = ""):
        weapon = self.character_model.attacks[item]

        bonus_mod = await bonus_calc(0, "dmg", self.character_model.bonuses, item_name=item)
        # print(f"dmg die. {weapon['die_num']}")
        die_mod = await bonus_calc(int(weapon["die_num"]), "dmg_die", self.character_model.bonuses, item_name=item)
        # print(die_mod)

        dmg_mod = 0
        match weapon["stat"]:
            case None:
                dmg_mod = 0
            case "":
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

        # Applicable to NPCs
        if "dmg_bonus" in weapon.keys():
            dmg_mod = dmg_mod + weapon["dmg_bonus"]

        die = weapon["die"]
        if die[0] != "d":
            die = f"d{die}"

        # Special Trait categories
        if weapon["prof"] != "NPC":
            for item in weapon["traits"]:
                if item.strip().lower() == "propulsive":
                    dmg_mod = int(dmg_mod)
                    if self.str_mod > 0:
                        dmg_mod += floor(self.str_mod / 2)
                    else:
                        dmg_mod += self.str_mod

        if crit:
            for item in weapon["traits"]:
                if "fatal" in item.strip().lower():
                    parsed_string = item.split("-")
                    die = parsed_string[1]
                    weapon["crit"] = f"*2+{parsed_string[1]}"
            return f"({die_mod}{die}+{dmg_mod}{ParseModifiers(f'{bonus_mod}')}{ParseModifiers(flat_bonus)}){weapon['crit']}"
        else:
            return f"{die_mod}{die}+{dmg_mod}{ParseModifiers(f'{bonus_mod}')}{ParseModifiers(flat_bonus)}"

    async def get_weapon(self, item):
        try:
            return self.character_model.attacks[item]
        except KeyError:
            return None

    async def is_complex_attack(self, item):
        # try:
        if "complex" in self.character_model.attacks[item].keys():
            if self.character_model.attacks[item]["complex"]:
                return True
        else:
            return False
        # except KeyError:
        #     return False

    async def clone_attack(self, attack, new_name, bonus_dmg, dmg_type):
        try:
            attk = await self.get_weapon(attack)
            original_attk = attk.copy()
            # print(original_attk)
            if "bonus" in original_attk.keys():
                bonus_list = original_attk["bonus"]
            else:
                bonus_list = []
            bonus_dict = {"damage": bonus_dmg, "dmg_type": dmg_type}
            bonus_list.append(bonus_dict)
            original_attk["bonus"] = bonus_list

            attacks = self.character_model.attacks
            # print(attacks)
            attacks[f"{attack} ({new_name})"] = original_attk
            # print(attacks)

            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

            Tracker = await get_EPF_tracker(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.char_name))
                character = char_result.scalars().one()
                character.attacks = attacks
                await session.commit()
            await self.update()
            return True
        except Exception as e:
            logging.warning(f"epf clone_attack {e}")
            return False

    async def get_spell_mod(self, spell, mod: bool):
        """
        Returns the spell modifier for the spell
        :param spell: (string)
        :param mod: (bool) True = Modifier, False = DC
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

        spell_attack_bonus = await bonus_calc(0, "spellattack", self.character_model.bonuses)

        if spell_data["tradition"] == "NPC":
            # print(attk_stat)
            # print(self.character_model.level)
            # print(spell_data['proficiency'])
            # print(spell_attack_bonus)
            if mod:
                return attk_stat + self.character_model.level + spell_data["proficiency"] + spell_attack_bonus
            else:
                return attk_stat + self.character_model.level + spell_data["dc"] + spell_attack_bonus
        else:
            if mod:
                return attk_stat + self.character_model.level + spell_data["proficiency"] + spell_attack_bonus
            else:
                return 10 + attk_stat + self.character_model.level + spell_data["proficiency"] + spell_attack_bonus

    async def get_spell_dmg(self, spell: str, level: int, flat_bonus: str = ""):
        spell_data = self.character_model.spells[spell]
        # print(spell_data)
        spell_dmg_bonus = await bonus_calc(0, "spelldmg", self.character_model.bonuses)
        if spell_dmg_bonus != 0:
            flat_bonus = flat_bonus + f"+{spell_dmg_bonus}"
        dmg_dict = {}
        dmg_string = ""
        for x, key in enumerate(spell_data["damage"]):
            # print(f"{x}, {key}")
            # print(spell_data["damage"][key]["value"])
            dmg_type = spell_data["damage"][key]["dmg_type"]
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

                if type(spell_data["damage"][key]["value"]) == dict:
                    dmg_string = (
                        f"{spell_data['damage'][key]['value']['formula']}+{mod_stat}{ParseModifiers(flat_bonus) if x==0 else ''}"
                    )
                else:
                    dmg_string = (
                        f"{spell_data['damage'][key]['value']}+{mod_stat}{ParseModifiers(flat_bonus) if x==0 else ''}"
                    )

                dmg_dict[key] = {
                    "dmg_string": dmg_string,
                    "dmg_type": dmg_type,
                }

            else:
                if type(spell_data["damage"][key]["value"]) == dict:
                    dmg_string = f"{spell_data['damage'][key]['value']['formula']}{ParseModifiers(flat_bonus)}"
                else:
                    dmg_string = f"{spell_data['damage'][key]['value']}{ParseModifiers(flat_bonus)}"
                dmg_dict[key] = {
                    "dmg_string": dmg_string,
                    "dmg_type": dmg_type,
                }
            # Heightening Calculations
        if level > spell_data["level"] and spell_data["heightening"]["type"] == "interval":
            # print(level)
            # print(spell_data["level"])
            if spell_data["level"] == 0:
                base_level = 1
            else:
                base_level = spell_data["level"]
            differance = level - base_level
            # print(differance)
            steps = floor(differance / spell_data["heightening"]["interval"])
            # print(steps)
            for i in range(0, steps):
                # print(i)
                # print(spell_data["heightening"]["damage"])
                for x, key in enumerate(spell_data["heightening"]["damage"]):
                    dmg_dict[key][
                        "dmg_string"
                    ] = f"{dmg_dict[key]['dmg_string']}+{spell_data['heightening']['damage'][key]}"
            # print(dmg_dict)
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
                    dmg_dict[item]["dmg_string"] += f"+{extra_dmg}"

        return dmg_dict

    async def get_spell_dmg_type(self, spell):
        spell_data = self.character_model.spells[spell]
        for key in spell_data["damage"].keys():
            return spell_data["damage"][key]["dmg_type"].lower()

    async def get_dc(self, item):
        if item == "AC":
            return self.ac_total
        elif item == "Fort" or item == "fort":
            return 10 + self.fort_mod
        elif item == "Reflex" or item == "reflex":
            return 10 + self.reflex_mod
        elif item == "Will" or item == "will":
            return 10 + self.will_mod
        elif item == "DC" or item == "dc":
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
        update: bool = True,
        target: str = None,
    ):
        logging.info("set_cc")
        # Get the Character's data

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)

        if target is None:
            target = self.char_name
            target_id = self.character_model.id
        else:
            Tracker = await get_EPF_tracker(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                result = await session.execute(select(Tracker.id).where(func.lower(Tracker.name) == target.lower()))
                target_id = result.scalars().one()

        # Check to make sure there isn't a condition with the same name on the character
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == self.id).where(Condition.title == title)
            )
            check_con = result.scalars().all()
            if len(check_con) > 0:
                return False

        # Process Data

        if title in EPF_Conditions:
            if data != "":
                if data[-1] != ",":
                    data = data + ","
            data = data + " " + EPF_Conditions[title]

        value = number
        stable = False
        eot = False
        if data != "":
            action = data.strip()
            action = action.lower()
            data_list = []

            try:
                tree = await condition_parser(action)
                data_list.append(await first_pass_process(self.ctx, tree, self.char_name))
            except Exception:
                processed_input = action.split(",")

                for item in processed_input:
                    try:
                        tree = await condition_parser(item)
                        data_list.append(await first_pass_process(self.ctx, tree, self.char_name))
                    except Exception as e:
                        print(f"Bad input: {item}: {e}")
            for item in data_list:
                if "value" in item.keys():
                    value = item["value"]

                if "stable" in item.keys():
                    stable = item["stable"]
                if "persist" in item.keys():
                    if item["persist"]:
                        eot = True

        # Write the condition to the table
        try:
            if not self.guild.timekeeping or unit == "Round":  # If its not time based, then just write it
                # print(f"Writing Condition: {title}")
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
                        target=target_id,
                        stable=stable,
                        value=value,
                        eot_parse=eot,
                    )
                    session.add(condition)
                await session.commit()
                if update:
                    await self.update()
                return True

            else:  # If its time based, then calculate the end time, before writing it
                if not stable:
                    value = None

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
                        target=target_id,
                        stable=stable,
                        value=value,
                        eot_parse=eot,
                    )
                    session.add(condition)
                await session.commit()
                if update:
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

    async def edit_cc(self, condition: str, value: int, **kwargs):
        """
        Edits the value of a condition associated with the character
        :param condition: string - Condition name
        :param value: integer - Value to set
        :return: boolean - True for success, False for failure
        """
        logging.info("edit_cc")
        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Condition).where(Condition.character_id == self.id).where(Condition.title == condition)
                )
                condition = result.scalars().one()

                if condition.time:
                    await self.ctx.send_followup(
                        "Unable to edit time based conditions. Try again in a future update.", ephemeral=True
                    )
                    return False
                else:
                    condition.number = value
                    if condition.stable is not True:
                        condition.value = value

                    await session.commit()
            return True
        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"edit_cc: {e}")
            return False

    async def update_resistance(self, weak, item, amount):
        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
        try:
            updated_resistance = self.resistance
            if amount == 0:
                async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                async with async_session() as session:
                    query = await session.execute(select(Condition).where(func.lower(Condition.item) == item.lower()))
                    condition_object = query.scalars().one()
                    await session.delete(condition_object)
                    await session.commit()
                return True
            else:
                condition_string = f"{item} {weak} {amount},"
                result = await self.set_cc(item, True, amount, "Round", False, data=condition_string, visible=False)

            await self.update()

            return True
        except Exception:
            return False

    async def show_resistance(self):
        embeds = []

        for key in self.resistance.keys():
            try:
                resist_string = ""
                for type in self.resistance[key].keys():
                    if type == "r":
                        resist_string += f"Resistance: {self.resistance[key][type]}\n"
                    elif type == "w":
                        resist_string += f"Weakness: {self.resistance[key][type]}\n"
                    elif type == "i":
                        resist_string += f"Immune\n"

                resist_embed = discord.Embed(
                    title=key.title(),
                    description=resist_string,
                )
                embeds.append(resist_embed)
            except Exception:
                pass

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
    async def set_init(self, init, **kwargs):
        if "update" in kwargs.keys():
            update = kwargs["update"]
        else:
            update = True

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
            if update:
                await self.update()
            return f"Initiative set to {init} for {self.char_name}"
        except Exception as e:
            logging.error(f"set_init: {e}")
            return f"Failed to set initiative: {e}"

    async def eot_parse(self, data):
        t = data.iter_subtrees_topdown()
        for branch in t:
            if branch.data == "skill_bonus":
                pass
            elif branch.data == "init_skill":
                pass
            elif branch.data == "new_condition":
                pass
            elif branch.data == "item_bonus":
                pass
            elif branch.data == "stable":
                pass
            elif branch.data == "set_value":
                pass
            elif branch.data == "temp_hp":
                pass

            elif branch.data == "resistance":
                pass
            elif branch.data == "persist_dmg":
                data = {}
                for item in branch.children:
                    if type(item) == lark.Tree:
                        if item.data == "roll_string":
                            roll_string = ""
                            for sub in item.children:
                                if sub is not None:
                                    roll_string = roll_string + sub.value

                            data["roll_string"] = roll_string
                        elif item.data == "save_string":
                            for sub in item.children:
                                data["save"] = sub.value
                    elif type(item) == lark.Token:
                        if item.type == "WORD":
                            data["dmg_type"] = item.value
                        elif item.type == "NUMBER":
                            data["save_value"] = item.value

        return data

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
                        value=f"{self.current_hp}/{self.max_hp}: ({self.temp_hp} Temp)\n",
                        inline=False,
                    ),
                    discord.EmbedField(name="Class: ", value=self.character_model.char_class, inline=False),
                    discord.EmbedField(name="Initiative: ", value=self.character_model.init_string, inline=False),
                ],
                color=discord.Color.dark_gold(),
            )
            embed.set_thumbnail(url=self.pic)
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


async def pb_import(ctx, engine, char_name, pb_char_code, guild=None, image=None):
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

        # print(initiative_num)
        # Check to see if character already exists, if it does, update instead of creating

        async with async_session() as session:
            query = await session.execute(select(EPF_tracker).where(func.lower(EPF_tracker.name) == char_name.lower()))
            character = query.scalars().all()
        if len(character) > 0:
            overwrite = True
            character = character[0]

        lores = ""
        for item, value in pb["build"]["lores"]:
            output = f"{item}, {value}; "
            lores += output

        feats = ""
        feat_list = []

        if "Air Element" in pb["build"]["specials"]:
            feat_list.append("Elemental Blast (Air)")
        if "Earth Element" in pb["build"]["specials"]:
            feat_list.append("Elemental Blast (Earth)")
        if "Fire Element" in pb["build"]["specials"]:
            feat_list.append("Elemental Blast (Fire)")
        if "Metal Element" in pb["build"]["specials"]:
            feat_list.append("Elemental Blast (Metal)")
        if "Water Element" in pb["build"]["specials"]:
            feat_list.append("Elemental Blast (Water)")
        if "Wood Element" in pb["build"]["specials"]:
            feat_list.append("Elemental Blast (Wood)")

        for item in pb["build"]["feats"]:
            print(item)
            feats += f"{item[0]}, "
            feat_list.append(item[0].strip())
        print(feat_list)

        bonus_dmg_list = []
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

            if len(item["extraDamage"]) > 0:
                for i in item["extraDamage"]:
                    bonus = i.split(" ")[0]
                    bonus_dmg_list.append(f"\"{item['display']}\" dmg {bonus} c")

            if "mat" in item.keys():
                if item["mat"] is None:
                    mat = ""
                else:
                    material = str(item["mat"])
                    parsed_mat = material.split("(")
                    mat = parsed_mat[0].strip()
            else:
                mat = ""

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
                "traits": [],
                "mat": mat,
            }

            if item["name"] in pb["build"]["specificProficiencies"]["trained"]:
                attacks[item["display"]]["override_prof"] = 2
            elif item["name"] in pb["build"]["specificProficiencies"]["expert"]:
                attacks[item["display"]]["override_prof"] = 4
            elif item["name"] in pb["build"]["specificProficiencies"]["master"]:
                attacks[item["display"]]["override_prof"] = 6
            elif item["name"] in pb["build"]["specificProficiencies"]["legendary"]:
                attacks[item["display"]]["override_prof"] = 8

            edited_attack = await attack_lookup(attacks[item["display"]], pb)

            double_attacks = False
            # Check for two handed and fatal
            if "traits" in edited_attack.keys():
                for trait in edited_attack["traits"]:
                    if "fatal-aim" in trait:
                        double_attacks = True
                        parsed_trait = trait.split("-")
                        fatal_die = parsed_trait[2]
                        attack_one = edited_attack.copy()
                        attack_two = edited_attack.copy()
                        trait_list = attack_one["traits"]
                        trait_copy = trait_list.copy()
                        for x, i in enumerate(trait_list):
                            if i == trait:
                                trait_copy[x] = f"fatal-{fatal_die}"

                        attack_one["traits"] = trait_copy
                        attack_one["display"] = f"{edited_attack['display']} (2H)"

                        trait_copy = []
                        for i in trait_list:
                            if i != trait:
                                trait_copy.append(i)

                        attack_two["display"] = f"{edited_attack['display']} (1H)"
                        attack_two["traits"] = trait_copy
                    if "two-hand" in trait:
                        double_attacks = True
                        parsed_trait = trait.split("-")
                        attk_2_die = parsed_trait[2]
                        attack_one = edited_attack.copy()
                        attack_two = edited_attack.copy()
                        attack_one["display"] = f"{edited_attack['display']} (2H)"
                        attack_one["die"] = attk_2_die
                        attack_two["display"] = f"{edited_attack['display']} (1H)"

            if double_attacks:
                del attacks[item["display"]]
                attacks[attack_one["display"]] = attack_one
                attacks[attack_two["display"]] = attack_two
            else:
                attacks[item["display"]] = edited_attack

        # print(attacks)

        # Spells
        spells_raw = pb["build"]["spellCasters"]
        focus_spells = pb["build"]["focus"]
        # print(focus_spells)
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
        for key in focus_spells.keys():
            # print(key)
            try:
                if type(focus_spells[key]) == dict:
                    if "wis" in focus_spells[key].keys():
                        if "focusSpells" in focus_spells[key]["wis"].keys():
                            discriminator = "focusSpells"
                        elif "focusCantrips" in focus_spells[key]["wis"].keys():
                            discriminator = "focusCantrips"
                        else:
                            discriminator = None
                        if discriminator is not None:
                            for item in focus_spells[key]["wis"]["focusSpells"]:
                                if "(Amped)" in item:
                                    lookup_name = item.strip("(Amped)")
                                else:
                                    lookup_name = item
                                spell_data = await spell_lookup(lookup_name)
                                if spell_data[0] is True:
                                    spell = {
                                        "level": 0,
                                        "tradition": key,
                                        "ability": "wis",
                                        "proficiency": focus_spells[key]["wis"]["proficiency"],
                                        "type": spell_data[1].type,
                                        "save": spell_data[1].save,
                                        "damage": spell_data[1].damage,
                                        "heightening": spell_data[1].heightening,
                                    }
                                    spell_library[item] = spell
                    if "cha" in focus_spells[key].keys():
                        if "focusSpells" in focus_spells[key]["cha"].keys():
                            discriminator = "focusSpells"
                        elif "focusCantrips" in focus_spells[key]["cha"].keys():
                            discriminator = "focusCantrips"
                        else:
                            discriminator = None
                        if discriminator is not None:
                            for item in focus_spells[key]["cha"][discriminator]:
                                # print(item)
                                if "(Amped)" in item:
                                    # print("amped")
                                    lookup_name = item.strip("(Amped)")
                                else:
                                    # print("not amped")
                                    lookup_name = item
                                # print(lookup_name)
                                spell_data = await spell_lookup(lookup_name)
                                # print(spell_data[0])
                                if spell_data[0] is True:
                                    spell = {
                                        "level": 0,
                                        "tradition": key,
                                        "ability": "cha",
                                        "proficiency": focus_spells[key]["cha"]["proficiency"],
                                        "type": spell_data[1].type,
                                        "save": spell_data[1].save,
                                        "damage": spell_data[1].damage,
                                        "heightening": spell_data[1].heightening,
                                    }
                                    spell_library[item] = spell

                    if "int" in focus_spells[key].keys():
                        if "focusSpells" in focus_spells[key]["int"].keys():
                            discriminator = "focusSpells"
                        elif "focusCantrips" in focus_spells[key]["int"].keys():
                            discriminator = "focusCantrips"
                        else:
                            discriminator = None
                        if discriminator is not None:
                            for item in focus_spells[key]["int"]["focusSpells"]:
                                if "(Amped)" in item:
                                    lookup_name = item.strip("(Amped)")
                                else:
                                    lookup_name = item
                                spell_data = await spell_lookup(lookup_name)
                                if spell_data[0] is True:
                                    spell = {
                                        "level": 0,
                                        "tradition": key,
                                        "ability": "itl",
                                        "proficiency": focus_spells[key]["int"]["proficiency"],
                                        "type": spell_data[1].type,
                                        "save": spell_data[1].save,
                                        "damage": spell_data[1].damage,
                                        "heightening": spell_data[1].heightening,
                                    }
                                    spell_library[item] = spell

            except Exception as e:
                pass

        # Kineticist Specific Code (at least for now:
        # print(Kineticist_DB.keys())
        for feat in feat_list:
            feat_data = await EPF_retreive_complex_data(feat)
            for x in feat_data:
                attacks[x.display_name] = x.data

        if overwrite:
            async with async_session() as session:
                query = await session.execute(
                    select(EPF_tracker).where(func.lower(EPF_tracker.name) == char_name.lower())
                )
                character = query.scalars().one()

                # Write the data from the JSON
                character.max_hp = (
                    pb["build"]["attributes"]["ancestryhp"]
                    + pb["build"]["attributes"]["classhp"]
                    + pb["build"]["attributes"]["bonushp"]
                    + pb["build"]["attributes"]["bonushpPerLevel"]
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
                if image is not None:
                    character.pic = image

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
                            + pb["build"]["attributes"]["bonushpPerLevel"]
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
                            + pb["build"]["attributes"]["bonushpPerLevel"]
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
                        pic=image,
                    )
                    session.add(new_char)
                await session.commit()

        await delete_intested_items(char_name, ctx, guild, engine)
        for item in pb["build"]["equipment"]:
            await invest_items(item[0], char_name, ctx, guild, engine)
        await write_bonuses(ctx, engine, guild, char_name, bonus_dmg_list)

        await calculate(ctx, engine, char_name, guild=guild)
        Character = await get_EPF_Character(char_name, ctx, guild, engine)
        # await Character.update()

        if guild.initiative is not None:
            # print("In initiative")
            try:
                await Character.roll_initiative()
            except Exception:
                logging.error("Error Rolling Initiative")

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
    # bonuses, resistance = await parse_bonuses(ctx, engine, char_name, guild=guild)
    bonuses, resistance = await parse(ctx, engine, char_name, guild=guild)
    # print(bonuses)

    async with async_session() as session:
        try:
            query = await session.execute(select(PF2_tracker).where(func.lower(PF2_tracker.name) == char_name.lower()))
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
                character.itl_mod, "crafting", character.crafting_prof, character.level, bonuses, ui
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

            init_skill = character.perception_mod

            if "other" in bonuses.keys():
                if "init_skill" in bonuses["other"].keys():
                    match bonuses["other"]["init_skill"]:
                        case "perception":
                            init_skill = character.perception_mod
                        case "acrobatics":
                            init_skill = character.acrobatics_mod
                        case "arcana":
                            init_skill = character.arcana_mod
                        case "athletics":
                            init_skill = character.athletics_mod
                        case "crafting":
                            init_skill = character.crafting_mod
                        case "deception":
                            init_skill = character.deception_mod
                        case "diplomacy":
                            init_skill = character.diplomacy_mod
                        case "intimidation":
                            init_skill = character.intimidation_mod
                        case "medicine":
                            init_skill = character.medicine_mod
                        case "nature":
                            init_skill = character.nature_mod
                        case "occultism":
                            init_skill = character.occultism_mod
                        case "performance":
                            init_skill = character.performance_mod
                        case "religion":
                            init_skill = character.religion_mod
                        case "society":
                            init_skill = character.society_mod
                        case "stealth":
                            init_skill = character.stealth_mod
                        case "survival":
                            init_skill = character.survival_mod
                        case "thievery":
                            init_skill = character.thievery_mod
                        case _:
                            init_skill = character.perception_mod

            character.init_string = f"1d20+{await bonus_calc(init_skill, 'init', bonuses)}"

            character.bonuses = bonuses
            character.resistance = resistance
            # print(character.bonuses)

            macros = []
            for item in character.attacks.keys():
                # print(item)
                macros.append(item)
            # for item in character.spells.keys():
            #     macros.append(f"Spell Attack: {item['name']}")
            macros.extend(PF2_skills)

            lore_list = character.lores.split(";")
            # print(lore_list)
            for item in lore_list:
                parsed_item = item.split(",")
                # print(parsed_item)
                if len(parsed_item) > 1:
                    # print(parsed_item[0])
                    macros.append(f"Lore: {parsed_item[0]}")

            Macro = await get_macro(ctx, engine, id=guild.id)
            async with async_session() as macro_session:
                result = await macro_session.execute(select(Macro.name).where(Macro.character_id == character.id))
                macro_list = result.scalars().all()
            macros.extend(macro_list)

            macro_string = ""
            for item in macros:
                macro_string += f"{item},"
            character.macros = macro_string
            # print(macro_string)

            await session.commit()

        except Exception as e:
            logging.warning(f"pf2 - enchanced character importer: {e}")


async def ability_mod_calc(base: int, item: str, bonuses):
    mod = floor((base - 10) / 2)
    if item in bonuses.keys():
        for key in bonuses[item].keys():
            mod = mod + bonuses[item][key]

    return mod


async def save_mod_calc(stat_mod, save: str, save_prof, level, bonuses):
    mod = stat_mod + save_prof + level
    if save in bonuses.keys():
        for key in bonuses[save].keys():
            mod = mod + bonuses[save][key]
    return mod


async def skill_mod_calc(stat_mod, skill: str, skill_prof, level, bonuses, ui):
    if skill_prof == 0 and not ui:
        mod = stat_mod
    elif skill_prof == 0 and ui:
        if level < 7:
            mod = stat_mod + math.floor(level / 2)
        else:
            mod = stat_mod + level
    else:
        mod = stat_mod + skill_prof + level

    if skill in bonuses.keys():
        for key in bonuses[skill].keys():
            mod = mod + bonuses[skill][key]
    return mod


async def bonus_calc(base, skill, bonuses, item_name=""):
    mod = base
    skill = skill.lower()

    if item_name != "":
        specific_skill = f"{item_name},{skill}".lower()

        if specific_skill in bonuses.keys():
            if skill in bonuses.keys():
                common_keys = bonuses[specific_skill].items() & bonuses[skill].items()

                for key in common_keys:
                    if abs(bonuses[specific_skill][key]) > abs(bonuses[skill][key]):
                        mod = mod + bonuses[specific_skill][key]

                for key in bonuses[specific_skill].keys():
                    if key not in common_keys:
                        mod = mod + bonuses[specific_skill][key]
                for key in bonuses[skill].keys():
                    if key not in common_keys:
                        mod = mod + bonuses[skill][key]

            else:
                for key in bonuses[specific_skill].keys():
                    mod = mod + bonuses[specific_skill][key]

    else:
        if skill in bonuses.keys():
            for key in bonuses[skill].keys():
                mod = mod + bonuses[skill][key]

    return mod


class EPF_Weapon(LookupBase):
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


class EPF_Equipment(LookupBase):
    __tablename__ = "EPF_equipment_data"
    # Columns
    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(), unique=True)
    level = Column(Integer())
    data = Column(JSON())


class EPF_Spells(LookupBase):
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
    # print(attack["display"])
    try:
        display_name = attack["display"].strip()
        async with async_session() as session:
            result = await session.execute(
                select(EPF_Weapon).where(func.lower(EPF_Weapon.name) == display_name.lower())
            )
            data = result.scalars().one()
    except Exception:
        try:
            # print(attack["name"])
            item_name = attack["name"].strip()
            async with async_session() as session:
                result = await session.execute(
                    select(EPF_Weapon).where(func.lower(EPF_Weapon.name) == item_name.lower())
                )
                data = result.scalars().one()
        except Exception as e:
            return attack
    # print(data.name, data.range, data.traits)

    # await lookup_engine.dispose()

    if data.range is not None:
        if "thrown" in data.traits:
            attack["stat"] = "str"
            attack["attk_stat"] = "dex"
        else:
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
    # print(attack)
    return attack


async def delete_intested_items(character, ctx, guild, engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    EPF_Tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    async with async_session() as session:
        char_result = await session.execute(
            select(EPF_Tracker.id).where(func.lower(EPF_Tracker.name) == character.lower())
        )
        id = char_result.scalars().one()
    async with async_session() as session:
        results = await session.execute(
            select(Condition)
            .where(Condition.character_id == id)
            .where(Condition.visible == false())
            .where(Condition.counter == true())
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
                # print(data)
                for key in data.keys():
                    if key in EPF_SKills:
                        if data[key]["mode"] == "item":
                            condition_string += f"{key} {ParseModifiers(str(data[key]['bonus']))} i, "
        # await lookup_engine.dispose()
        if condition_string != "":
            # print(condition_string)
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
                # print("Committed")
            return True
        else:
            return False
    except Exception:
        # await engine.dispose()
        return False


async def write_bonuses(ctx, engine, guild, character: str, bonuses: list):
    bonus_string = ", ".join(bonuses)
    print(bonus_string)
    EPF_Tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    write_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with write_session() as write_session:
        char_result = await write_session.execute(
            select(EPF_Tracker.id).where(func.lower(EPF_Tracker.name) == character.lower())
        )
        id = char_result.scalars().one()

    async with write_session.begin():
        write_session.add(
            Condition(
                character_id=id,
                title="Weapon Bonuses",
                number=0,
                counter=True,
                visible=False,
                action=bonus_string,
            )
        )
        await write_session.commit()


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


grammer = """
start: phrase+

phrase: value+ break

value: (WORD | COMBO_WORD) (SIGNED_INT | VARIABLE )  SPECIFIER         -> skill_bonus
    | "init-skill" WORD                                                -> init_skill
    | "hardness" NUMBER                                                -> hardness
    | quoted (WORD | COMBO_WORD) SIGNED_INT SPECIFIER                  -> item_bonus
    | "thp" NUMBER                                                     -> temp_hp
    | (WORD | COMBO_WORD) SPECIFIER NUMBER? ";"?                       -> resistance
    | (WORD | COMBO_WORD) SPECIFIER NUMBER? "e" WORD ";"?              -> resistance_w_exception
    | "stable" NUMBER?                                                 -> stable
    | persist_dmg                       
    | WORD NUMBER?                                                     -> new_condition

persist_dmg : ("persistent dmg" | "pd") roll_string WORD* ["/" "dc" NUMBER save_string]

modifier: SIGNED_INT

quoted: SINGLE_QUOTED_STRING
    | DOUBLE_QUOTED_STRING

break: ","


roll_string: ROLL (POS_NEG ROLL)* [POS_NEG NUMBER]
!save_string: "reflex" | "fort" | "will" | "flat"

ROLL: NUMBER "d" NUMBER 

POS_NEG : ("+" | "-")

DOUBLE_QUOTED_STRING  : /"[^"]*"/
SINGLE_QUOTED_STRING  : /'[^']*'/

SPECIFIER : "c" | "s" | "i" | "r" | "w"
VARIABLE : "+x" | "-x" 


COMBO_WORD : WORD ("-" |"_") WORD
%import common.ESCAPED_STRING
%import common.WORD
%import common.SIGNED_INT
%import common.NUMBER
%import common.WS
%ignore WS
"""


async def condition_parser(data: str):
    # print(data)
    if data[-1:] != ",":
        data = data + ","

    parser = Lark(grammer)
    return parser.parse(data)


async def process_condition_tree(
    ctx: discord.ApplicationContext, tree, character_model, condition, bonuses: dict, resistances: dict
):
    t = tree.iter_subtrees_topdown()
    for branch in t:
        if branch.data == "skill_bonus":
            bonus_data = {}
            for item in branch.children:
                if type(item) == lark.Token:
                    if item.type == "WORD":
                        bonus_data["skill"] = item.value
                    elif item.type == "SIGNED_INT":
                        bonus_data["value"] = int(item.value)
                    elif item.type == "VARIABLE":
                        if condition.value is not None:
                            bonus_data["value"] = int(f"{item.value[0]}{condition.value}")
                        else:
                            bonus_data["value"] = int(f"{item.value[0]}{condition.number}")
                    elif item.type == "SPECIFIER":
                        bonus_data["specifier"] = item.value

            if bonus_data["skill"] not in bonuses.keys():
                bonuses[bonus_data["skill"]] = {
                    f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}": bonus_data["value"]
                }
            else:
                if (
                    f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}"
                    in bonuses[bonus_data["skill"]].keys()
                ):
                    if abs(bonus_data["value"]) > abs(
                        bonuses[bonus_data["skill"]][
                            f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}"
                        ]
                    ):
                        bonuses[bonus_data["skill"]][
                            f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}"
                        ] = bonus_data["value"]
                else:
                    bonuses[bonus_data["skill"]][
                        f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}"
                    ] = bonus_data["value"]
            # print(bonuses)

        elif branch.data == "init_skill":
            if "other" in bonuses.keys():
                bonuses["other"]["init_skill"] = branch.children[0].value
            else:
                bonuses["other"] = {"init_skill": branch.children[0].value}
            # print(bonuses)

        elif branch.data == "hardness":
            print("HARDNESS")
            print(branch.children)
            if "other" in bonuses.keys():
                bonuses["other"]["hardness"] = int(branch.children[0].value)
            else:
                bonuses["other"] = {"hardness": int(branch.children[0].value)}

        elif branch.data == "new_condition":
            new_con_name = ""
            num = 0
            for item in branch.children:
                if item.type == "WORD":
                    new_con_name = item.value
                elif item.type == "NUMBER":
                    num = item.value

            if new_con_name.title() in EPF_Conditions.keys():
                if new_con_name.title() not in await character_model.conditions():
                    await character_model.set_cc(new_con_name.title(), False, num, "Round", False)

        elif branch.data == "item_bonus":
            bonus_data = {}
            for item in branch.children:
                if type(item) == lark.Token:
                    if item.type == "quoted":
                        bonus_data["item"] = item.value.strip('"')
                    if item.type == "WORD":
                        bonus_data["skill"] = item.value
                    elif item.type == "SIGNED_INT":
                        bonus_data["value"] = int(item.value)
                    elif item.type == "VARIABLE":
                        bonus_data["value"] = condition.number
                    elif item.type == "SPECIFIER":
                        bonus_data["specifier"] = item.value
                elif type(item) == lark.Tree:
                    bonus_data["item"] = item.children[0].value

            if f"{bonus_data['item']},{bonus_data['skill']}" not in bonuses.keys():
                bonuses[f"{bonus_data['item']},{bonus_data['skill']}"] = {
                    f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}": bonus_data["value"]
                }
            else:
                if (
                    f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}"
                    in bonuses[f"{bonus_data['item']},{bonus_data['skill']}"].keys()
                ):
                    if abs(bonus_data["value"]) > abs(
                        bonuses[f"{bonus_data['item']},{bonus_data['skill']}"][
                            f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}"
                        ]
                    ):
                        bonuses[f"{bonus_data['item']},{bonus_data['skill']}"][
                            f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}"
                        ] = bonus_data["value"]
                else:
                    bonuses[f"{bonus_data['item']},{bonus_data['skill']}"][
                        f"{bonus_data['specifier']}{'+' if bonus_data['value'] > 0 else '-'}"
                    ] = bonus_data["value"]
            # print(bonuses)

        elif branch.data == "stable":
            stable_value = None
            for item in branch.children:
                if type(item) == lark.Token:
                    if item.type == "NUMBER":
                        stable_value = int(item.value)
            # print(f"output: stable {stable_value}")

            if not condition.stable:
                async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                Condition = await get_condition(ctx, engine, id=None)

                async with async_session() as session:
                    result = await session.execute(select(Condition).where(Condition.id == condition.id))
                    this_condition = result.scalars().one()

                    this_condition.stable = True
                    if stable_value is not None:
                        this_condition.value = stable_value
                    else:
                        this_condition.value = this_condition.number

                    await session.commit()

        # Will be addressed on the first pass interpreter
        elif branch.data == "temp_hp":
            # for item in branch.children:
            #     print("temp hp", item.value)
            pass

        elif branch.data == "resistance":
            temp = {"value": 0}
            resistance_data = {}

            for item in branch.children:
                if item.type == "WORD" or item.type == "COMBO_WORD":
                    temp["word"] = item.value
                elif item.type == "SPECIFIER":
                    temp["specifier"] = item.value
                elif item.type == "NUMBER":
                    temp["value"] = int(item.value)

            resistance_data[temp["word"]] = {temp["specifier"]: temp["value"]}

            if temp["word"] in resistances.keys():
                if temp["specifier"] in resistances[temp["word"]].keys():
                    if temp["value"] > resistances[temp["word"]][temp["specifier"]]:
                        resistances[temp["word"]][temp["specifier"]] = temp["value"]
                else:
                    resistances[temp["word"]][temp["specifier"]] = temp["value"]
            else:
                resistances[temp["word"]] = {temp["specifier"]: temp["value"]}

        elif branch.data == "resistance_w_exception":
            temp = {"value": 0}
            resistance_data = {}
            for x, item in enumerate(branch.children):
                if item.type == "WORD" or item.type == "COMBO_WORD":
                    if x == 0:
                        temp["word"] = item.value
                    else:
                        temp["exception"] = item.value
                elif item.type == "SPECIFIER":
                    temp["specifier"] = item.value
                elif item.type == "NUMBER":
                    temp["value"] = int(item.value)

            resistance_data[temp["word"]] = {temp["specifier"]: temp["value"], "except": temp["exception"]}
            # print("resistance data", resistance_data)

            if temp["word"] in resistances.keys():
                if temp["specifier"] in resistances[temp["word"]].keys():
                    if temp["value"] > resistances[temp["word"]][temp["specifier"]]:
                        resistances[temp["word"]][temp["specifier"]] = {
                            "value": temp["value"],
                            "except": temp["exception"],
                        }
                else:
                    resistances[temp["word"]][temp["specifier"]] = {"value": temp["value"], "except": temp["exception"]}
            else:
                resistances[temp["word"]] = resistance_data[temp["word"]]

        # print(bonuses)
        # print(resistances)

    return bonuses, resistances


async def first_pass_process(ctx: discord.ApplicationContext, tree, character_name):
    character_model = await get_EPF_Character(character_name, ctx)
    data = {}
    t = tree.iter_subtrees_topdown()
    for branch in t:
        if branch.data == "skill_bonus":
            pass
        elif branch.data == "init_skill":
            pass
        elif branch.data == "new_condition":
            pass
        elif branch.data == "item_bonus":
            pass
        elif branch.data == "stable":
            stable_value = None
            for item in branch.children:
                if type(item) == lark.Token:
                    if item.type == "NUMBER":
                        stable_value = int(item.value)
            data["stable"] = True
            data["value"] = stable_value

        elif branch.data == "set_value":
            for item in branch.children:
                if item.type == "NUMBER":
                    data["value"] = int(item.value)

        elif branch.data == "temp_hp":
            for item in branch.children:
                await character_model.add_thp(item.value)

        elif branch.data == "resistance":
            pass
        elif branch.data == "persist_dmg":
            data["persist"] = True

    return data


async def parse(ctx, engine, char_name: str, guild=None):
    bonuses = {}
    resistances = {}
    guild = await get_guild(ctx, guild=guild)
    Character_Model = await get_EPF_Character(char_name, ctx, guild=guild, engine=engine)

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

    for condition in conditions:
        await asyncio.sleep(0)
        # print(condition.action)
        if condition.action != "":
            action = condition.action
            action = action.strip()
            action = action.lower()
            try:
                tree = await condition_parser(action)
                # print(tree.pretty())
                bonuses, resistances = await process_condition_tree(
                    ctx, tree, Character_Model, condition, bonuses, resistances
                )
            except Exception:
                processed_input = action.split(",")
                for item in processed_input:
                    try:
                        tree = await condition_parser(item)
                        bonuses, resistances = await process_condition_tree(
                            ctx, tree, Character_Model, condition, bonuses, resistances
                        )
                    except Exception as e:
                        logging.error(f"Bad input: {item}: {e}")

    # print(bonuses, "\n", resistances)
    return bonuses, resistances
