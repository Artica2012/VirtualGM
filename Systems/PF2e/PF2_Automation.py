import logging

import d20
import discord
from sqlalchemy.exc import NoResultFound

from Systems.Base.Automation import Automation, AutoOutput
from Systems.PF2e.pf2_functions import PF2_base_dc, PF2_eval_succss
from Backend.utils.error_handling_reporting import error_not_initialized
from Backend.utils.Char_Getter import get_character
from Backend.utils.Macro_Getter import get_macro_object
from Backend.utils.parsing import ParseModifiers


class PF2_Automation(Automation):
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
            Macro_Model = await get_macro_object(self.ctx, guild=self.guild)
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
            case "DC":
                con_vs = Target_Model.dc

        goal_value = con_vs + (PF2_base_dc if vs in ["Fort", "Will", "Reflex"] else 0)

        try:
            goal_string: str = f"({goal_value}){ParseModifiers(target_modifier)}"
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

        raw_output = {
            "string": output_string,
            "success": success_string,
            "roll": str(dice_result.result),
            "roll_total": int(dice_result.total),
        }

        embed = discord.Embed(
            title=f"{char_model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
            color=color,
        )
        embed.set_thumbnail(url=char_model.pic)

        output = AutoOutput(embed=embed, raw=raw_output)

        return output

    async def save(self, character, target, save, dc, modifier):
        if target is None:
            embed = discord.Embed(title=character, fields=[discord.EmbedField(name=save, value="Invalid Target")])

            return embed

        orig_dc = dc
        Character_Model = await get_character(character, self.ctx, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, guild=self.guild)
        con_vs = 0
        match save:
            case "AC":
                con_vs = Target_Model.ac
            case "Fort":
                con_vs = Target_Model.fort
            case "Reflex":
                con_vs = Target_Model.reflex
            case "Will":
                con_vs = Target_Model.will
            case "DC":
                con_vs = Target_Model.dc

        try:
            roll = f"1d20+{con_vs}"
            # print(roll)

            if dc is None:
                dc = Character_Model.dc
                if Character_Model.dc is None:
                    dc = 0
            # print(dc)
            try:
                dice_result = d20.roll(roll)
                goal_string: str = f"{dc}{ParseModifiers(modifier)}"
                goal_result = d20.roll(goal_string)
            except Exception as e:
                logging.warning(f"attack: {e}")
                return False

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
            elif Character_Model.player == True:
                output_string = (
                    f"{target} makes a DC{dc} {save} save!\n{character} forced the"
                    f" save.\n{dice_result}\n{success_string}"
                )
            else:
                output_string = (
                    f"{target} makes a {save} save!\n{character} forced the save.\n{dice_result}\n{success_string}"
                )

            raw_output = {
                "string": output_string,
                "success": success_string,
                "roll": str(dice_result.result),
                "roll_total": int(dice_result.total),
            }

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False

        embed = discord.Embed(
            title=(
                f"{Character_Model.char_name} vs {Target_Model.char_name}"
                if character != target
                else f"{Character_Model.char_name}"
            ),
            fields=[discord.EmbedField(name=save, value=output_string)],
            color=color,
        )
        embed.set_thumbnail(url=Character_Model.pic)

        return AutoOutput(embed=embed, raw=raw_output)
