import logging

import d20
import discord
from sqlalchemy.exc import NoResultFound

from Systems.Base.Automation import Automation, AutoOutput
from Systems.STF.STF_Character import get_STF_Character, STF_Character
from Systems.STF.STF_Support import STF_eval_success
from Backend.utils.error_handling_reporting import error_not_initialized
from Backend.utils.Char_Getter import get_character
from Backend.utils.parsing import ParseModifiers


class STF_Automation(Automation):
    def __init__(self, ctx, guild):
        super().__init__(ctx, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier, multi=False):
        char_model = await get_character(character, self.ctx, guild=self.guild)
        try:
            roll_string: str = f"{roll}{ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)
        except Exception:
            roll_string = f"({await char_model.get_roll(roll)}){ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)

        opponent = await get_character(target, self.ctx, guild=self.guild)
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

        raw_output = {
            "string": output_string,
            "success": success_string,
            "roll": str(dice_result.roll),
            "roll_total": int(dice_result.total),
        }

        embed = discord.Embed(
            title=f"{char_model.char_name} vs {opponent.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
        )
        embed.set_thumbnail(url=char_model.pic)

        return AutoOutput(embed=embed, raw=raw_output)

    async def save(self, character, target, save, dc, modifier):
        if target is None:
            embed = discord.Embed(title=character, fields=[discord.EmbedField(name=save, value="Invalid Target")])

            return embed

        attacker = await get_STF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        opponent = await get_STF_Character(target, self.ctx, guild=self.guild, engine=self.engine)

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
            success_string = STF_eval_success(dice_result, goal_result)
            # Format output string
            if character == target:
                output_string = f"{character} makes a {save} save!\n{dice_result}\n{success_string if orig_dc else ''}"
            else:
                output_string = (
                    f"{target} makes a {save} save!\n{character} forced the save.\n{dice_result}\n{success_string}"
                )

            raw_output = {
                "string": output_string,
                "success": success_string,
                "roll": str(dice_result.roll),
                "roll_total": int(dice_result.total),
            }

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False

        embed = discord.Embed(
            title=f"{attacker.char_name} vs {opponent.char_name}" if character != target else f"{attacker.char_name}",
            fields=[discord.EmbedField(name=save, value=output_string)],
        )
        embed.set_thumbnail(url=attacker.pic)

        return AutoOutput(embed=embed, raw=raw_output)

    async def damage(self, bot, character, target, roll, modifier, healing, damage_type: str, crit=False, multi=False):
        Character_Model = await get_character(character, self.ctx, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, guild=self.guild)
        weapon = None

        try:
            roll_result: d20.RollResult = d20.roll(f"({roll}){ParseModifiers(modifier)}")
        except Exception:
            try:
                roll_result = d20.roll(f"({await Character_Model.weapon_dmg(roll)}){ParseModifiers(modifier)}")
                # print(roll_result)
                weapon = await Character_Model.get_weapon(roll)
            except Exception:
                try:
                    # print(e)
                    roll_result = d20.roll(f"{await Character_Model.get_roll(roll)}{ParseModifiers(modifier)}")
                except Exception:
                    roll_result = d20.roll("0 [Error]")
        dmg = roll_result.total
        if not healing:
            dmg = await damage_calc_resist(dmg, damage_type, Target_Model, weapon=weapon)
        output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"

        raw_output = {
            "string": output_string,
            "success": "",
            "roll": str(roll_result.roll),
            "roll_total": int(roll_result.total),
        }

        embed = discord.Embed(
            title=f"{Character_Model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
        )
        embed.set_thumbnail(url=Character_Model.pic)

        await Target_Model.change_hp(dmg, healing, post=True)

        return AutoOutput(embed=embed, raw=raw_output)


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
