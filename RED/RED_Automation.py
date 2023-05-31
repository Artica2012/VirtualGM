import logging

import d20
import discord

from Base.Automation import Automation
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.parsing import ParseModifiers
from RED.RED_Support import RED_Roll_Result, RED_eval_success


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
        range=None,
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
        print(dice_result.total)
        if "(autofire)" in attack:
            autofire = True
        else:
            autofire = False

        weapon = await Character_Model.get_weapon(attack)

        goal_value = await Character_Model.red_get_auto_dv(weapon, range, Target_Model, autofire=autofire)
        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            goal_result = RED_Roll_Result(d20.roll(goal_string))
            print(goal_result.total)
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
        dmg: RED_Roll_Result = await Character_Model.weapon_damage(attack, dmg_modifier)

        if success_string == "Success":
            amt = await Target_Model.damage_armor(dmg, location)
            color = color.green()
            dmg_output_string = f"{character} damages {target} for: {dmg}"
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

        if not multi:
            await Tracker_Model.update_pinned_tracker()
        return embed
