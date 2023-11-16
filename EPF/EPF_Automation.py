import logging
from math import floor

import d20
import discord
import lark
from lark import Lark

import EPF.EPF_Character
from Base.Automation import Automation
from EPF.Attack_Class import get_attack
from EPF.EPF_Character import get_EPF_Character
from EPF.EPF_Support import EPF_Conditions
from EPF.EPF_resists import damage_calc_resist
from PF2e.pf2_functions import PF2_eval_succss
from utils.Tracker_Getter import get_tracker_model
from utils.parsing import ParseModifiers
from utils.utils import get_guild


class EPF_Automation(Automation):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier, multi=False):
        Attack = await get_attack(character, roll, self.ctx, guild=self.guild)
        return await Attack.roll_attack(target, vs, attack_modifier, target_modifier)

    async def save(self, character, target, save, dc, modifier):
        Attack = await get_attack(character, save, self.ctx, guild=self.guild)
        return await Attack.save(target, dc, modifier)

    async def damage(self, bot, character, target, roll, modifier, healing, damage_type: str, crit=False, multi=False):
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        if roll == "Treat Wounds":
            return await treat_wounds(
                self.ctx, character, target, damage_type, modifier, engine=self.engine, guild=self.guild
            )

        Attack = await get_attack(character, roll, self.ctx, guild=self.guild)
        embed = await Attack.damage(target, modifier, healing, damage_type, crit)

        if not multi:
            await Tracker_Model.update_pinned_tracker()
        return embed

    async def auto(
        self,
        bot,
        character,
        target,
        attack,
        attack_modifier,
        target_modifier,
        dmg_modifier,
        dmg_type_override,
        multi=False,
    ):
        logging.info("/a auto")
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)

        Attack = await get_attack(character, attack, self.ctx, guild=self.guild)
        embed = await Attack.auto(target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override)

        if not multi:
            await Tracker_Model.update_pinned_tracker()
        return embed

    async def cast(
        self,
        bot,
        character,
        target,
        spell_name,
        level,
        attack_modifier,
        target_modifier,
        dmg_modifier,
        dmg_type_override,
        multi=False,
    ):
        logging.info("/a cast")
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        Character_Model = await get_EPF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        Target_Model = await get_EPF_Character(target, self.ctx, guild=self.guild, engine=self.engine)
        spell = Character_Model.character_model.spells[spell_name]
        total_damage = 0
        color = discord.Color(value=125)

        # Attack
        if spell["type"] == "attack":
            attack_roll = d20.roll(
                f"1d20+{await Character_Model.get_spell_mod(spell_name, True)}{ParseModifiers(attack_modifier)}"
            )
            goal_result = d20.roll(f"{Target_Model.ac_total}{ParseModifiers(target_modifier)}")

            success_string = PF2_eval_succss(attack_roll, goal_result)
            attk_output_string = f"{character} casts {spell_name} at {target}:\n{attack_roll}\n{success_string}"

            if success_string == "Critical Success" and "critical-hits" not in Target_Model.resistance["immune"]:
                dmg_string, total_damage = await roll_spell_dmg_resist(
                    Character_Model,
                    Target_Model,
                    spell_name,
                    level,
                    True,
                    flat_bonus=dmg_modifier,
                    dmg_type_override=dmg_type_override,
                )
                color = color.gold()
            elif success_string == "Success" or success_string == "Critical Success":
                dmg_string, total_damage = await roll_spell_dmg_resist(
                    Character_Model,
                    Target_Model,
                    spell_name,
                    level,
                    False,
                    flat_bonus=dmg_modifier,
                    dmg_type_override=dmg_type_override,
                )
                color = color.green()
            else:
                dmg_string = None
                color = color.red()

        elif spell["type"] == "save":
            save_type = spell["save"]["value"]
            save_dc = d20.roll(
                f"{await Character_Model.get_spell_mod(spell_name, False)}{ParseModifiers(attack_modifier)}"
            )
            roll = d20.roll(f"{await Target_Model.get_roll(save_type.title())}{ParseModifiers(target_modifier)}")

            success_string = PF2_eval_succss(roll, save_dc)
            attk_output_string = (
                f"{character} casts {spell_name}.\n"
                f"{target} makes a {save_type.title()} save!\n{character} forced the save.\n{roll}\n{success_string}"
            )
            if success_string == "Critical Failure":
                dmg_string, total_damage = await roll_spell_dmg_resist(
                    Character_Model,
                    Target_Model,
                    spell_name,
                    level,
                    True,
                    flat_bonus=dmg_modifier,
                    dmg_type_override=dmg_type_override,
                )
                color = color.gold()
            elif success_string == "Failure":
                dmg_string, total_damage = await roll_spell_dmg_resist(
                    Character_Model,
                    Target_Model,
                    spell_name,
                    level,
                    False,
                    flat_bonus=dmg_modifier,
                    dmg_type_override=dmg_type_override,
                )
                color = color.green()
            elif success_string == "Success":
                dmg_string, orig_total_damage = await roll_spell_dmg_resist(
                    Character_Model,
                    Target_Model,
                    spell_name,
                    level,
                    False,
                    flat_bonus=dmg_modifier,
                    dmg_type_override=dmg_type_override,
                )
                for key in dmg_string.keys():
                    dmg_string[key]["damage_string"] = f"{dmg_string[key]['damage_string']}/2"
                total_damage = floor(int(orig_total_damage) / 2)
                color = color.red()
            else:
                dmg_string = None
        else:
            return False
        # Damage

        if dmg_string is not None:
            dmg_output_string = f"{character} damages {target} for:\n"
            for key in dmg_string.keys():
                dmg_type: str = dmg_string[key]["damage_type"]
                dmg_output_string += f"{dmg_string[key]['damage_roll']} {dmg_type.title()}\n"

            await Target_Model.change_hp(total_damage, heal=False, post=False)
            if Target_Model.player:
                output = (
                    f"{attk_output_string}\n{dmg_output_string}{Target_Model.char_name} damaged for"
                    f" {total_damage}.New HP: {Target_Model.current_hp}/{Target_Model.max_hp}"
                )
            else:
                output = (
                    f"{attk_output_string}\n{dmg_output_string}{Target_Model.char_name} damaged for {total_damage}."
                    f" {await Target_Model.calculate_hp()}"
                )
        else:
            output = attk_output_string

        embed = discord.Embed(
            title=f"{Character_Model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=f"{spell_name} {level}", value=output)],
            color=color,
        )
        embed.set_thumbnail(url=Character_Model.pic)

        if not multi:
            await Tracker_Model.update_pinned_tracker()
        return embed


async def roll_spell_dmg_resist(
    Character_Model: EPF.EPF_Character.EPF_Character,
    Target_Model: EPF.EPF_Character.EPF_Character,
    spell: str,
    level: int,
    crit: bool,
    flat_bonus="",
    dmg_type_override=None,
):
    """
    Rolls damage and calculates resists
    :param Character_Model:
    :param Target_Model:
    :param attack:
    :param crit:
    :return: Tuple of damage_output_string(string), total_damage(int)
    """
    logging.info("roll_dmg_spell_resist")
    # Roll the critical damage and apply resistances
    dmg_rolls = {}
    # print(spell, crit)
    if crit and "critical-hits" not in Target_Model.resistance["immune"]:
        spell_dmg = await Character_Model.get_spell_dmg(spell, level, flat_bonus=flat_bonus)
        # print(spell_dmg)
        for key in spell_dmg.keys():
            if dmg_type_override is not None:
                dmg_type = dmg_type_override
            else:
                dmg_type = spell_dmg[key]["dmg_type"]

            dmg_rolls[key] = {}
            dmg_rolls[key]["damage_string"] = spell_dmg[key]["dmg_string"]
            dmg_rolls[key]["damage_roll"] = d20.roll(f"({dmg_rolls[key]['damage_string']})*2")
            dmg_rolls[key]["damage_type"] = dmg_type
    else:
        spell_dmg = await Character_Model.get_spell_dmg(spell, level, flat_bonus=flat_bonus)
        # print(spell_dmg)

        for key in spell_dmg.keys():
            if dmg_type_override is not None:
                dmg_type = dmg_type_override
            else:
                dmg_type = spell_dmg[key]["dmg_type"]

            dmg_rolls[key] = {}
            dmg_rolls[key]["damage_string"] = spell_dmg[key]["dmg_string"]
            dmg_rolls[key]["damage_roll"] = d20.roll(f"{dmg_rolls[key]['damage_string']}")
            dmg_rolls[key]["damage_type"] = dmg_type

    total_damage = 0
    for key in spell_dmg.keys():
        total_damage += await damage_calc_resist(
            dmg_rolls[key]["damage_roll"].total, dmg_rolls[key]["damage_type"], Target_Model
        )

    # print(dmg_output_string, total_damage)
    return dmg_rolls, total_damage


async def treat_wounds(ctx, character, target, dc, modifier, engine, guild=None):
    Character_Model = await get_EPF_Character(character, ctx, engine=engine, guild=guild)
    Target_Model = await get_EPF_Character(target, ctx, engine=engine, guild=guild)
    # print("treat wounds")
    guild = await get_guild(ctx, guild)
    roll_string = f"{await Character_Model.get_roll('Medicine')}{ParseModifiers(modifier)}"
    # print(roll_string)
    medicine_roll = d20.roll(roll_string)
    if dc == "":
        dc = "15"
    goal = d20.roll(dc)
    output_string = "ERROR."

    # print(medicine_roll)

    success_string = PF2_eval_succss(medicine_roll, goal)

    # print(success_string)

    if success_string == "Success":
        if dc == "40":
            healing = d20.roll("2d8+50")
        elif dc == "30":
            healing = d20.roll("2d8+30")
        elif dc == "20":
            healing = d20.roll("2d8+10")
        else:
            healing = d20.roll("2d8")
        # print(healing.total)
        # print(type(healing.total))
        await Target_Model.change_hp(healing.total, heal=True, post=False)
        output_string = (
            f"{Character_Model.char_name} uses Treat Wounds on {Target_Model.char_name}.\n"
            f"{medicine_roll} {success_string}.\n"
            f"{healing}\n"
            f"{Target_Model.char_name} healed for {healing.total}."
        )
    elif success_string == "Critical Success":
        if dc == "40":
            healing = d20.roll("4d8+50")
        elif dc == "30":
            healing = d20.roll("4d8+30")
        elif dc == "20":
            healing = d20.roll("4d8+10")
        else:
            healing = d20.roll("4d8")

        await Target_Model.change_hp(healing.total, heal=True, post=False)
        output_string = (
            f"{Character_Model.char_name} uses Treat Wounds on {Target_Model.char_name}.\n"
            f"{medicine_roll} {success_string}.\n"
            f"{healing}\n"
            f"{Target_Model.char_name} healed for {healing.total}."
        )

    elif success_string == "Critical Failure":
        dmg = d20.roll("1d8")
        await Target_Model.change_hp(dmg.total, heal=False, post=False)
        output_string = (
            f"{Character_Model.char_name} uses Treat Wounds on {Target_Model.char_name}.\n"
            f"{medicine_roll} {success_string}.\n {dmg}\n"
            f"{Target_Model.char_name} damaged for {dmg.total}."
        )
    else:
        output_string = (
            f"{Character_Model.char_name} uses Treat Wounds on {Target_Model.char_name}.\n"
            f"{medicine_roll}\n"
            f"{success_string}.\n"
        )
    # print(guild.timekeeping)
    if guild.timekeeping:
        if "continual recovery" in Character_Model.character_model.feats.lower():
            time = 10
        else:
            time = 60
        await Target_Model.set_cc("Wounds Treated", False, time, "Minute", True)

    Tracker_Model = await get_tracker_model(ctx, None, guild=guild, engine=engine)
    await Tracker_Model.update_pinned_tracker()

    embed = discord.Embed(title="Treat Wounds", description=output_string)
    embed.set_thumbnail(url=Character_Model.pic)

    return embed


attack_grammer = """
start: phrase+

phrase: value+ break

value: roll_string WORD                                                -> damage_string
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


async def automation_parse(data, target_model):
    processed_data = {}
    try:
        if data[-1:] != ",":
            data = data + ","

        tree = Lark(attack_grammer).parse(data)
        print(tree.pretty())
        processed_data = await parse_automation_tree(tree, processed_data, target_model)
    except Exception:
        processed_input = data.split(",")
        for item in processed_input:
            # try:
            if data[-1:] != ",":
                data = data + ","

            tree = Lark(attack_grammer).parse(data)
            print(tree.pretty())
            processed_data = await parse_automation_tree(tree, processed_data, target_model)
            # except Exception as e:
            #     logging.error(f"Bad input: {item}: {e}")

    return processed_data


async def parse_automation_tree(tree, data: dict, target_model):
    t = tree.iter_subtrees_topdown()
    for branch in t:
        if branch.data == "new_condition":
            # TODO Update syntax to allow duration and data etc in new conditions.
            #  This can then be put back into the condition parser
            new_con_name = ""
            num = 0
            for item in branch.children:
                if item.type == "WORD":
                    new_con_name = item.value
                elif item.type == "NUMBER":
                    num = item.value

            if new_con_name.title() in EPF_Conditions.keys():
                if new_con_name.title() not in await target_model.conditions():
                    await target_model.set_cc(new_con_name.title(), False, num, "Round", False)

                data["condition"] = new_con_name

        elif branch.data == "persist_dmg":
            temp = {}
            for item in branch.children:
                if type(item) == lark.Tree:
                    if item.data == "roll_string":
                        roll_string = ""
                        for sub in item.children:
                            if sub is not None:
                                roll_string = roll_string + sub.value

                        temp["roll_string"] = roll_string
                    elif item.data == "save_string":
                        for sub in item.children:
                            temp["save"] = sub.value
                elif type(item) == lark.Token:
                    if item.type == "WORD":
                        temp["dmg_type"] = item.value
                    elif item.type == "NUMBER":
                        temp["save_value"] = item.value
            data["pd"] = temp

        elif branch.data == "damage_string":
            if "dmg" not in data.keys():
                data["dmg"] = {}

            temp = {}
            for item in branch.children:
                # print(item)
                if type(item) == lark.Tree:
                    if item.data == "roll_string":
                        roll_string = ""
                        for sub in item.children:
                            if sub is not None:
                                roll_string = roll_string + sub.value

                        temp["roll_string"] = roll_string
                elif type(item) == lark.Token:
                    if item.type == "WORD":
                        temp["dmg_type"] = item.value

            if temp["dmg_type"] is not None and temp["roll_string"] is not None:
                data["dmg"][temp["dmg_type"]] = temp["roll_string"]

    return data


async def scripted_damage_roll_resists(
    data: dict, Target_Model: EPF.EPF_Character.EPF_Character, crit: bool, flat_bonus="", dmg_type_override=None
):
    dmg_output = []
    total_damage = 0
    for x, key in enumerate(data["dmg"]):
        dmg_string = f"({data['dmg'][key]}{ParseModifiers(flat_bonus) if x == 0 else ''}){'*2' if crit else ''}"
        damage_roll = d20.roll(dmg_string)

        if dmg_type_override == "":
            dmg_type_override = None
        if dmg_type_override is not None:
            base_dmg_type = dmg_type_override
        else:
            base_dmg_type = key
        total_damage += await damage_calc_resist(damage_roll.total, base_dmg_type, Target_Model)
        dmg_output_string = f"{damage_roll}"
        output = {"dmg_output_string": dmg_output_string, "dmg_type": base_dmg_type}
        dmg_output.append(output)

    return dmg_output, total_damage
