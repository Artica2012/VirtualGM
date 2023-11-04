import logging
from math import floor

import d20
import discord
from sqlalchemy.exc import NoResultFound

import EPF.EPF_Character
from Base.Automation import Automation
from EPF.EPF_Character import get_EPF_Character
from EPF.EPF_resists import damage_calc_resist, roll_dmg_resist
from PF2e.pf2_functions import PF2_eval_succss
from error_handling_reporting import error_not_initialized
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.parsing import ParseModifiers
from utils.utils import get_guild


class EPF_Automation(Automation):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier, multi=False):
        char_model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
        try:
            roll_string: str = f"{roll}{ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)
        except Exception:
            roll_string = f"({await char_model.get_roll(roll)}){ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)

        opponent = await get_character(target, self.ctx, guild=self.guild, engine=self.engine)
        goal_value = await opponent.get_dc(vs)

        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"attack: {e}")
            return "Error"

        # Format output string
        success_string = PF2_eval_succss(dice_result, goal_result)
        if success_string == "Critical Success":
            color = discord.Color.gold()
        elif success_string == "Success":
            color = discord.Color.green()
        elif success_string == "Failure":
            color = discord.Color.red()
        else:
            color = discord.Color.dark_red()
        output_string = f"{character} rolls {roll} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"

        embed = discord.Embed(
            title=f"{char_model.char_name} vs {opponent.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
            color=color,
        )
        embed.set_thumbnail(url=char_model.pic)

        return embed

    async def save(self, character, target, save, dc, modifier):
        if target is None:
            embed = discord.Embed(title=character, fields=[discord.EmbedField(name=save, value="Invalid Target")])

            return embed
        attacker = await get_EPF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        opponent = await get_EPF_Character(target, self.ctx, guild=self.guild, engine=self.engine)

        orig_dc = dc

        if dc is None:
            dc = await attacker.get_dc("DC")
        try:
            dice_result = d20.roll(f"{await opponent.get_roll(save)}{ParseModifiers(modifier)}")
            goal_result = d20.roll(f"{dc}")
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False
        try:
            success_string = PF2_eval_succss(dice_result, goal_result)

            if success_string == "Critical Success":
                color = discord.Color.gold()
            elif success_string == "Success":
                color = discord.Color.green()
            elif success_string == "Failure":
                color = discord.Color.red()
            else:
                color = discord.Color.dark_red()

            # Format output string
            if character == target:
                output_string = f"{character} makes a {save} save!\n{dice_result}\n{success_string if orig_dc else ''}"
            else:
                output_string = (
                    f"{target} makes a {save} save!\n{character} forced the save.\n{dice_result}\n{success_string}"
                )

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False

        embed = discord.Embed(
            title=f"{attacker.char_name} vs {opponent.char_name}" if character != target else f"{attacker.char_name}",
            fields=[discord.EmbedField(name=save, value=output_string)],
            color=color,
        )
        embed.set_thumbnail(url=attacker.pic)

        return embed

    async def damage(self, bot, character, target, roll, modifier, healing, damage_type: str, crit=False, multi=False):
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)
        weapon = None
        # print(roll)
        if roll == "Treat Wounds":
            return await treat_wounds(
                self.ctx, character, target, damage_type, modifier, engine=self.engine, guild=self.guild
            )

        try:
            roll_result: d20.RollResult = d20.roll(f"({roll}){ParseModifiers(modifier)}")
            dmg = roll_result.total
            if not healing:
                dmg = await damage_calc_resist(dmg, damage_type, Target_Model, weapon=weapon)
            roll_string = f"{roll_result} {damage_type}"
        except Exception:
            try:
                dmg_output, total_damage = await roll_dmg_resist(
                    Character_Model, Target_Model, roll, crit, modifier, dmg_type_override=damage_type
                )
                roll_string = ""
                for item in dmg_output:
                    roll_string += f"{item['dmg_output_string']} {item['dmg_type'].title()}\n"
                dmg = total_damage
            except Exception:
                try:
                    roll_result = d20.roll(f"{await Character_Model.get_roll(roll)}{ParseModifiers(modifier)}")
                    dmg = roll_result.total
                    if not healing:
                        dmg = await damage_calc_resist(dmg, damage_type, Target_Model, weapon=weapon)
                    roll_string = f"{roll_result} {damage_type}"
                except Exception:
                    roll_result = d20.roll("0 [Error]")
                    dmg = roll_result.total
                    roll_string = roll_result

        await Target_Model.change_hp(dmg, healing, post=False)
        output_string = (
            f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_string}"
            f"\n{f'{dmg} Damage' if not healing else f'{dmg} Healed'}\n"
            f"{await Target_Model.calculate_hp()}"
        )

        embed = discord.Embed(
            title=f"{Character_Model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
        )
        embed.set_thumbnail(url=Character_Model.pic)

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
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)
        color = discord.Color(value=125)

        # Attack
        roll_string = f"({await Character_Model.get_roll(attack)})"
        dice_result = d20.roll(f"{roll_string}{ParseModifiers(attack_modifier)}")

        goal_value = Target_Model.ac_total
        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"auto: {e}")
            return "Error"

        # Format output string

        success_string = PF2_eval_succss(dice_result, goal_result)
        attk_output_string = (
            f"{character} attacks {target} {'' if target_modifier == '' else f'(AC {target_modifier})' } with their"
            f" {attack}:\n{dice_result}\n{success_string}"
        )

        # Damage
        if success_string == "Critical Success" and "critical-hits" not in Target_Model.resistance.keys():
            dmg_string, total_damage = await roll_dmg_resist(
                Character_Model,
                Target_Model,
                attack,
                True,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
            )
            color = color.gold()
        elif success_string == "Success" or success_string == "Critical Success":
            dmg_string, total_damage = await roll_dmg_resist(
                Character_Model,
                Target_Model,
                attack,
                False,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
            )
            color = color.green()
        else:
            if success_string == "Failure":
                color = color.red()
            else:
                color = color.dark_red()
            dmg_string = None
            total_damage = 0

        if dmg_string is not None:
            dmg_output_string = f"{character} damages {target} for:"
            # print(dmg_string)
            for item in dmg_string:
                dmg_output_string += f"\n{item['dmg_output_string']} {item['dmg_type'].title()}"
            await Target_Model.change_hp(total_damage, heal=False, post=False)
            if Target_Model.player:
                output = (
                    f"{attk_output_string}\n{dmg_output_string}\n{Target_Model.char_name} damaged for"
                    f" {total_damage}.New HP: {Target_Model.current_hp}/{Target_Model.max_hp}"
                )
            else:
                output = (
                    f"{attk_output_string}\n{dmg_output_string}\n{Target_Model.char_name} damaged for {total_damage}."
                    f" {await Target_Model.calculate_hp()}"
                )
        else:
            output = attk_output_string

        embed = discord.Embed(
            title=f"{Character_Model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=attack, value=output)],
            color=color,
        )
        embed.set_thumbnail(url=Character_Model.pic)

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
