import logging

import d20
from sqlalchemy.exc import NoResultFound

import EPF.EPF_Character
from Base.Automation import Automation
from EPF.EPF_Character import get_EPF_Character
from PF2e.pf2_functions import PF2_eval_succss
from error_handling_reporting import error_not_initialized
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.parsing import ParseModifiers


class EPF_Automation(Automation):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier):
        try:
            # if type(roll[0]) == int:
            roll_string: str = f"{roll}{ParseModifiers(attack_modifier)}"
            # print(roll_string)
            dice_result = d20.roll(roll_string)
        except Exception:
            char_model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
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
        output_string = f"{character} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
        return output_string

    async def save(self, character, target, save, dc, modifier):
        if target is None:
            output_string = "Error. No Target Specified."
            return output_string
        print(f" {save}, {dc}, {modifier}")
        attacker = await get_EPF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        opponent = await get_EPF_Character(target, self.ctx, guild=self.guild, engine=self.engine)

        orig_dc = dc

        if dc is None:
            dc = await attacker.get_dc("DC")
            print(dc)
        try:
            print(await opponent.get_roll(save))
            dice_result = d20.roll(f"{await opponent.get_roll(save)}{ParseModifiers(modifier)}")
            print(dice_result)
            # goal_string: str = f"{dc}"
            goal_result = d20.roll(f"{dc}")
            print(goal_result)
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False
        try:
            success_string = PF2_eval_succss(dice_result, goal_result)
            print(success_string)
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

        return output_string

    async def damage(self, bot, character, target, roll, modifier, healing, damage_type: str, crit=False):
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)
        try:
            roll_result: d20.RollResult = d20.roll(f"({roll}){ParseModifiers(modifier)}")
        except Exception:
            try:
                roll_result = d20.roll(f"({Character_Model.weapon_dmg(roll)}){ParseModifiers(modifier)}")
            except Exception:
                try:
                    roll_result = d20.roll(f"{Character_Model.get_roll(roll)}{ParseModifiers(modifier)}")
                except Exception:
                    roll_result = d20.roll("0 [Error]")
        dmg = roll_result.total
        if not healing:
            dmg = damage_calc_resist(dmg, damage_type, Target_Model)
        output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
        await Target_Model.change_hp(dmg, healing)
        await Tracker_Model.update_pinned_tracker()
        return output_string

    async def auto(self, bot, character, target, attack, attack_modifier, target_modifier):
        logging.info("/a auto")
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)

        # Attack
        roll_string = f"({await Character_Model.get_roll(attack)})"
        # print("roll string", roll_string)
        dice_result = d20.roll(f"{roll_string}{ParseModifiers(attack_modifier)}")

        goal_value = Target_Model.ac_total
        # print("goal value", goal_value)
        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            # print("goal string ", goal_string)
            goal_result = d20.roll(goal_string)
            # print(goal_result)
        except Exception as e:
            logging.warning(f"auto: {e}")
            return "Error"

        # Format output string

        success_string = PF2_eval_succss(dice_result, goal_result)
        # print(success_string)
        attk_output_string = f"{character} vs {target}:\n{dice_result}\n{success_string}"
        # print(attk_output_string)

        # Damage
        if success_string == "Critical Success":
            dmg_string, total_damage = await roll_dmg_resist(Character_Model, Target_Model, attack, True)
        elif success_string == "Success":
            dmg_string, total_damage = await roll_dmg_resist(Character_Model, Target_Model, attack, False)
        else:
            dmg_string = None

        weapon = await Character_Model.get_weapon(attack)
        if dmg_string is not None:
            dmg_output_string = f"{character} damages {target} for:\n{dmg_string} {weapon['dmg_type'].title()}"
            await Target_Model.change_hp(total_damage, heal=False, post=False)
            await Tracker_Model.update_pinned_tracker()
            if Target_Model.player:
                return (
                    f"{attk_output_string}\n{dmg_output_string}\n{Target_Model.char_name} damaged for"
                    f" {total_damage}.New HP: {Target_Model.current_hp}/{Target_Model.max_hp}"
                )
            else:
                return (
                    f"{attk_output_string}\n{dmg_output_string}\n{Target_Model.char_name} damaged for {total_damage}."
                    f" {await Target_Model.calculate_hp()}"
                )
        else:
            return attk_output_string


async def damage_calc_resist(dmg_roll, dmg_type, target: EPF.EPF_Character.EPF_Character):
    logging.info("damage_calc_resist")
    dmg = dmg_roll
    print(target.resistance)
    print(dmg_type)
    if (
        "physical" in target.resistance["resist"]
        or "physical" in target.resistance["weak"]
        or "physical" in target.resistance["immune"]
    ):
        print("Physical Resistance")
        if dmg_type.lower() == "slashing" or dmg_type.lower() == "piercing" or dmg_type.lower() == "bludgeoning":
            dmg_type = "physical"
            print(dmg_type)
    if dmg_type.lower() in target.resistance["resist"]:
        dmg = dmg - target.resistance["resist"][dmg_type]
        if dmg < 0:
            dmg = 0
    elif dmg_type.lower() in target.resistance["weak"]:
        dmg = dmg + target.resistance["weak"][dmg_type]
    elif dmg_type.lower() in target.resistance["immune"]:
        dmg = 0
    return dmg


async def roll_dmg_resist(
    Character_Model: EPF.EPF_Character.EPF_Character,
    Target_Model: EPF.EPF_Character.EPF_Character,
    attack: str,
    crit: bool,
):
    """
    Rolls damage and calculates resists
    :param Character_Model:
    :param Target_Model:
    :param attack:
    :param crit:
    :return: Tuple of damage_output_string(string), total_damage(int)
    """
    logging.info("roll_dmg_resist")
    # Roll the critical damage and apply resistances
    damage_roll = d20.roll(await Character_Model.weapon_dmg(attack, crit=crit))
    weapon = await Character_Model.get_weapon(attack)
    total_damage = await damage_calc_resist(damage_roll.total, weapon["dmg_type"].title(), Target_Model)
    dmg_output_string = f"{damage_roll}"
    # Check for bonus damage
    if "bonus" in Character_Model.character_model.attacks[attack]:
        for item in Character_Model.character_model.attacks[attack]["bonus"]:
            bonus_roll = d20.roll(item["damage"])
            bonus_damage = await damage_calc_resist(bonus_roll.total, item["dmg_type"])
            dmg_output_string = f"{dmg_output_string}+{bonus_roll}"
            total_damage += bonus_damage
    print(dmg_output_string, total_damage)
    return dmg_output_string, total_damage
