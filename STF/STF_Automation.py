import logging

import d20
from sqlalchemy.exc import NoResultFound

from Base.Automation import Automation
from STF.STF_Character import get_STF_Character, STF_Character
from error_handling_reporting import error_not_initialized
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.parsing import ParseModifiers
from STF.STF_Support import STF_eval_success


class STF_Automation(Automation):
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
        success_string = STF_eval_success(dice_result, goal_result)
        output_string = f"{character} rolls {roll} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
        return output_string

    async def save(self, character, target, save, dc, modifier):
        if target is None:
            output_string = "Error. No Target Specified."
            return output_string
        # print(f" {save}, {dc}, {modifier}")
        attacker = await get_STF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        opponent = await get_STF_Character(target, self.ctx, guild=self.guild, engine=self.engine)

        orig_dc = dc

        if dc is None:
            dc = await attacker.get_dc("DC")
            # print(dc)
        try:
            # print(await opponent.get_roll(save))
            dice_result = d20.roll(f"{await opponent.get_roll(save)}{ParseModifiers(modifier)}")
            # print(dice_result)
            # goal_string: str = f"{dc}"
            goal_result = d20.roll(f"{dc}")
            # print(goal_result)
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False
        try:
            success_string = STF_eval_success(dice_result, goal_result)
            # print(success_string)
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
        weapon = None

        try:
            roll_result: d20.RollResult = d20.roll(f"({roll}){ParseModifiers(modifier)}")
        except Exception:
            try:
                roll_result = d20.roll(f"({await Character_Model.weapon_dmg(roll)}){ParseModifiers(modifier)}")
                print(roll_result)
                weapon = await Character_Model.get_weapon(roll)
            except Exception as e:
                try:
                    print(e)
                    roll_result = d20.roll(f"{await Character_Model.get_roll(roll)}{ParseModifiers(modifier)}")
                except Exception:
                    roll_result = d20.roll("0 [Error]")
        dmg = roll_result.total
        if not healing:
            dmg = await damage_calc_resist(dmg, damage_type, Target_Model, weapon=weapon)
        output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
        await Target_Model.change_hp(dmg, healing, post=True)
        await Tracker_Model.update_pinned_tracker()
        return output_string


async def damage_calc_resist(dmg_roll, dmg_type, target: STF_Character, weapon=None):
    logging.info("damage_calc_resist")
    dmg_type = dmg_type.lower()
    if target.resistance == {"resist": {}, "weak": {}, "immune": {}}:
        return dmg_roll
    dmg = dmg_roll

    if dmg_type.lower() in target.resistance["resist"]:
        dmg = dmg - target.resistance["resist"][dmg_type]
        if dmg < 0:
            dmg = 0
    elif dmg_type.lower() in target.resistance["weak"]:
        dmg = dmg + target.resistance["weak"][dmg_type]
    elif dmg_type.lower() in target.resistance["immune"]:
        dmg = 0
    elif "all_damage" in target.resistance["resist"]:
        dmg = dmg - target.resistance["resist"]["all-damage"]
    elif "all-damage" in target.resistance["immune"]:
        dmg = 0

    return dmg
