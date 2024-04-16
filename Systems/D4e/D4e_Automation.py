import logging

import d20
import discord
from sqlalchemy.exc import NoResultFound

from Systems.Base.Automation import Automation, AutoOutput
from Systems.D4e.d4e_functions import D4e_eval_success, D4e_base_roll
from Backend.utils.error_handling_reporting import error_not_initialized
from Backend.utils.Char_Getter import get_character
from Backend.utils.Macro_Getter import get_macro_object
from Backend.utils.parsing import ParseModifiers


class D4e_Automation(Automation):
    def __init__(self, ctx, guild):
        super().__init__(ctx, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier, multi=False):
        # Strip a macro:
        roll_list = roll.split(":")
        # print(roll_list)
        if len(roll_list) == 1:
            roll = roll
        else:
            roll = roll_list[1]

        char_model = await get_character(character, self.ctx, guild=self.guild)

        try:
            Macro_Model = await get_macro_object(self.ctx, engine=self.engine, guild=self.guild)
            roll_string: str = f"({await Macro_Model.raw_macro(character, roll)}){ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)
        except:
            roll_string: str = f"({roll}){ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)

        Target_Model = await get_character(target, self.ctx, guild=self.guild)
        con_vs = 0
        match vs:  # noqa
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
        output_string = f"{character} rolls {roll} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"

        raw_output = {
            "string": output_string,
            "success": success_string,
            "roll": str(dice_result.result),
            "roll_total": int(dice_result.total),
        }

        embed = discord.Embed(
            title=f"{char_model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
        )
        embed.set_thumbnail(url=char_model.pic)

        return AutoOutput(embed=embed, raw=raw_output)

    async def save(self, character, target, save, dc, modifier):
        try:
            Character_Model = await get_character(character, self.ctx, guild=self.guild)
            roll_string = f"1d20{ParseModifiers(modifier)}"
            dice_result = d20.roll(roll_string)
            success_string = D4e_eval_success(dice_result, D4e_base_roll)
            # Format output string
            output_string = f"Save: {character}\n{dice_result}\n{success_string}"
            # CC modify
            if dice_result.total >= D4e_base_roll.total:
                await Character_Model.delete_cc(target)

            raw_output = {
                "string": output_string,
                "success": success_string,
                "roll": str(dice_result.result),
                "roll_total": int(dice_result.total),
            }

            embed = discord.Embed(
                title=f"{Character_Model.char_name}",
                fields=[discord.EmbedField(name=save, value=output_string)],
            )
            embed.set_thumbnail(url=Character_Model.pic)

            return AutoOutput(embed=embed, raw=raw_output)

        except NoResultFound:
            if self.ctx is not None:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"save: {e}")
            return False
