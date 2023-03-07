import logging

import d20
from sqlalchemy.exc import NoResultFound

from Base.Automation import Automation
from error_handling_reporting import error_not_initialized
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers
from D4e.d4e_functions import D4e_eval_success, D4e_base_roll


class D4e_Automation(Automation):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier):
        # Strip a macro:
        roll_list = roll.split(":")
        # print(roll_list)
        if len(roll_list) == 1:
            roll = roll
        else:
            roll = roll_list[1]

        roll_string: str = f"({roll}){ParseModifiers(attack_modifier)}"
        dice_result = d20.roll(roll_string)

        Target_Model = await get_character(target, self.ctx, guild=self.guild, engine=self.engine)
        con_vs = 0
        match vs:
            case "AC":
                con_vs = Target_Model.ac
            case "Fort":
                con_vs = Target_Model.fort
            case "Reflex":
                con_vs = Target_Model.reflex
            case "Will":
                con_vs = Target_Model.will

        try:
            goal_string: str = f"({con_vs}){ParseModifiers(target_modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"attack: {e}")
            return "Error"

        # Format output string
        success_string = D4e_eval_success(dice_result, goal_result)
        output_string = f"{character} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
        return output_string

    async def save(self, character, target, save, dc, modifier):

        try:
            Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
            roll_string = f"1d20{ParseModifiers(modifier)}"
            dice_result = d20.roll(roll_string)
            success_string = D4e_eval_success(dice_result, D4e_base_roll)
            # Format output string
            output_string = f"Save: {character}\n{dice_result}\n{success_string}"
            # CC modify
            if dice_result.total >= D4e_base_roll.total:
                await Character_Model.delete_cc(target)

            return output_string

        except NoResultFound:
            if self.ctx is not None:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return "Error"
        except Exception as e:
            logging.warning(f"save: {e}")
            return "Error"



