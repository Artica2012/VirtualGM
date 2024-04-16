import logging

import d20
import discord

from Systems.Base.Automation import Automation, AutoOutput
from Systems.EPF.Attack_Class import get_attack, get_spell, AutoModel
from Systems.EPF.EPF_Character import get_EPF_Character
from Systems.PF2e.pf2_functions import PF2_eval_succss
from Backend.utils.Tracker_Getter import get_tracker_model
from Backend.utils.parsing import ParseModifiers
from Backend.utils.utils import get_guild


class EPF_Automation(Automation):
    def __init__(self, ctx, guild):
        super().__init__(ctx, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier, multi=False):
        Attack = await get_attack(character, roll, self.ctx, guild=self.guild)
        return await Attack.roll_attack(target, vs, attack_modifier, target_modifier)

    async def save(self, character, target, save, dc, modifier):
        Attack = await get_attack(character, save, self.ctx, guild=self.guild)
        return await Attack.save(target, dc, modifier)

    async def damage(self, bot, character, target, roll, modifier, healing, damage_type: str, crit=False, multi=False):
        if roll == "Treat Wounds":
            return await treat_wounds(
                self.ctx, character, target, damage_type, modifier, engine=self.engine, guild=self.guild
            )

        Attack = await get_attack(character, roll, self.ctx, guild=self.guild)
        embed = await Attack.damage(target, modifier, healing, damage_type, crit)

        # if not multi:
        #     await Tracker_Model.update_pinned_tracker()
        return embed

    async def auto(
        self,
        bot,
        character,
        target,
        attack,
        attack_modifier,
        target_modifier,
        dmg_modifier,
        dmg_type_override,
        multi=False,
    ):
        logging.info("/a auto")

        Attack = await get_attack(character, attack, self.ctx, guild=self.guild)
        embed = await Attack.auto(target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override)

        return embed

    async def cast(
        self,
        bot,
        character,
        target,
        spell_name,
        level,
        attack_modifier,
        target_modifier,
        dmg_modifier,
        dmg_type_override,
        multi=False,
    ):
        logging.info("/a cast")

        Spell = await get_spell(character, spell_name, level, self.ctx, guild=self.guild)
        return await Spell.cast(target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override)


async def treat_wounds(ctx, character, target, dc, modifier, engine, guild=None):
    Character_Model = await get_EPF_Character(character, ctx, guild=guild)
    Target_Model = await get_EPF_Character(target, ctx, guild=guild)
    # print("treat wounds")
    guild = await get_guild(ctx, guild)
    total = 0
    roll_string = f"{await Character_Model.get_roll('Medicine')}{ParseModifiers(modifier)}"
    # print(roll_string)
    medicine_roll = d20.roll(roll_string)
    if dc == "":
        dc = "15"
    goal = d20.roll(dc)
    output_string = "ERROR."

    # print(medicine_roll)

    success_string = PF2_eval_succss(medicine_roll, goal)

    # print(success_string)

    if success_string == "Success":
        if dc == "40":
            healing = d20.roll("2d8+50")
        elif dc == "30":
            healing = d20.roll("2d8+30")
        elif dc == "20":
            healing = d20.roll("2d8+10")
        else:
            healing = d20.roll("2d8")
        # print(healing.total)
        # print(type(healing.total))
        await Target_Model.change_hp(healing.total, heal=True, post=False)
        output_string = (
            f"{Character_Model.char_name} uses Treat Wounds on {Target_Model.char_name}.\n"
            f"{medicine_roll} {success_string}.\n"
            f"{healing}\n"
            f"{Target_Model.char_name} healed for {healing.total}."
        )
    elif success_string == "Critical Success":
        if dc == "40":
            healing = d20.roll("4d8+50")
        elif dc == "30":
            healing = d20.roll("4d8+30")
        elif dc == "20":
            healing = d20.roll("4d8+10")
        else:
            healing = d20.roll("4d8")
        total = healing

        await Target_Model.change_hp(healing.total, heal=True, post=False)
        output_string = (
            f"{Character_Model.char_name} uses Treat Wounds on {Target_Model.char_name}.\n"
            f"{medicine_roll} {success_string}.\n"
            f"{healing}\n"
            f"{Target_Model.char_name} healed for {healing.total}."
        )

    elif success_string == "Critical Failure":
        dmg = d20.roll("1d8")
        await Target_Model.change_hp(dmg.total, heal=False, post=False)
        output_string = (
            f"{Character_Model.char_name} uses Treat Wounds on {Target_Model.char_name}.\n"
            f"{medicine_roll} {success_string}.\n {dmg}\n"
            f"{Target_Model.char_name} damaged for {dmg.total}."
        )
        total = dmg
    else:
        output_string = (
            f"{Character_Model.char_name} uses Treat Wounds on {Target_Model.char_name}.\n"
            f"{medicine_roll}\n"
            f"{success_string}.\n"
        )
    # print(guild.timekeeping)
    if guild.timekeeping:
        if "continual recovery" in Character_Model.character_model.feats.lower():
            time = 10
        else:
            time = 60
        await Target_Model.set_cc("Wounds Treated", False, time, "Minute", True)

    Tracker_Model = await get_tracker_model(ctx, guild=guild)
    await Tracker_Model.update_pinned_tracker()

    embed = discord.Embed(
        title=f"{character} treats wounds on {Target_Model.char_name}",
        fields=[discord.EmbedField(name="Treat Wounds", value=output_string)],
        color=AutoModel.success_color(success_string),
    )

    embed.set_thumbnail(url=Character_Model.pic)

    raw_output = {
        "string": output_string,
        "success": success_string,
        "roll": f"Treat Wounds {dc}",
        "roll_total": int(total),
    }
    return AutoOutput(embed=embed, raw=raw_output)
