import logging

import d20
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Automation import Automation
from PF2e.pf2_functions import PF2_eval_succss
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers


class EPF_Automation(Automation):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier):
        try:
            # if type(roll[0]) == int:
            roll_string: str = f"{roll}{ParseModifiers(attack_modifier)}"
            print(roll_string)
            dice_result = d20.roll(roll_string)
        except:
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


