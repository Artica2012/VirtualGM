import logging

import d20
import discord

from Base.Automation import Automation
from RED.RED_Support import RED_Roll_Result, RED_eval_success
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.parsing import ParseModifiers


class RED_Automation(Automation):
    def __int__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def auto(
        self,
        bot,
        character,
        target,
        attack,
        attack_modifier,
        target_modifier,
        dmg_modifier,
        multi=False,
        range_value=None,
        location="Body",
    ):
        logging.info("/red auto")
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)
        color = discord.Color(value=125)

        # Attack
        roll_string = f"({await Character_Model.get_roll(attack)})"
        dice_result = RED_Roll_Result(d20.roll(f"{roll_string}{ParseModifiers(attack_modifier)}"))
        # print(dice_result.total)
        if "(Autofire)" in attack:
            autofire = True
        else:
            autofire = False
        # print(f"Autofire: {autofire}")

        weapon = await Character_Model.get_weapon(attack)

        goal_value = await Character_Model.red_get_auto_dv(weapon, range_value, Target_Model, autofire=autofire)
        # print(goal_value)
        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            goal_result = RED_Roll_Result(d20.roll(goal_string))
        except Exception as e:
            logging.warning(f"auto: {e}")
            return "Error"

        # Format output string

        success_string = RED_eval_success(dice_result, goal_result)
        attk_output_string = (
            f"{character} attacks {target} {'' if target_modifier == '' else f'( {target_modifier})'} with their"
            f" {attack} ({location}):\n{dice_result}\n{success_string}"
        )

        # Damage
        # Roll Damage

        if success_string == "Success":
            if autofire:
                diff = dice_result - goal_result
                if diff > weapon["autofire_ammt"]:
                    diff = weapon["autofire_ammt"]
                elif diff == 0:
                    diff = 1

                dmg = await Character_Model.weapon_damage(attack, dmg_modifier, iter=diff)
            else:
                dmg = await Character_Model.weapon_damage(attack, dmg_modifier)

            amt = await Target_Model.damage_armor(dmg, location)
            color = color.green()
            dmg_output_string = f"{dmg}"
            if Target_Model.player:
                output = (
                    f"{attk_output_string}\n{dmg_output_string}\n{Target_Model.char_name} damaged for"
                    f" {amt}. {f'New HP: {Target_Model.current_hp}/{Target_Model.max_hp}' if amt > 0 else ''}"
                )
            else:
                output = (
                    f"{attk_output_string}\n{dmg_output_string}\n{Target_Model.char_name} damaged for {amt}."
                    f" {await Target_Model.calculate_hp()}"
                )
        else:
            color = color.red()
            output = attk_output_string

        embed = discord.Embed(
            title=f"{Character_Model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=attack, value=output)],
            color=color,
        )
        embed.set_thumbnail(url=Character_Model.pic)

        print(multi)
        if not multi:
            print("Updating")
            await Tracker_Model.update_pinned_tracker()
        return embed

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier, multi=False):
        # Strip a macro:
        roll_list = roll.split(":")
        # print(roll_list)
        if len(roll_list) == 1:
            roll = roll
        else:
            roll = roll_list[1]

        char_model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
        try:
            dice_result = RED_Roll_Result(
                d20.roll(f"{await char_model.get_roll(roll)}{ParseModifiers(attack_modifier)}")
            )
            print(dice_result)
        except Exception:
            roll_string: str = f"({roll}){ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)

        Target_Model = await get_character(target, self.ctx, guild=self.guild, engine=self.engine)

        goal_value = await Target_Model.get_roll(vs)
        print(goal_value)

        try:
            goal_string: str = f"({goal_value}){ParseModifiers(target_modifier)}"
            goal_result = RED_Roll_Result(d20.roll(goal_string))
        except Exception as e:
            logging.warning(f"attack: {e}")
            return "Error"

        # Format output string
        success_string = RED_eval_success(dice_result, goal_result)

        if success_string == "Success":
            color = discord.Color.green()
        else:
            color = discord.Color.red()

        output_string = f"{character} rolls {roll} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"

        embed = discord.Embed(
            title=f"{char_model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
            color=color,
        )
        embed.set_thumbnail(url=char_model.pic)

        return embed
