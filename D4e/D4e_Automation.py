import logging

import d20

from Base.Automation import Automation
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers
from D4e.d4e_functions import D4e_eval_success


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



