# automation_cog.py

import logging

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands

from auto_complete import (
    character_select,
    character_select_gm,
    a_macro_select,
    get_attributes,
    a_save_target_custom,
    save_select,
    dmg_type,
    spell_list,
    spell_level,
)
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.Automation_Getter import get_automation


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# UTILITY FUNCTIONS

# Checks to see if the user of the slash command is the GM, returns a boolean


class AutomationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ---------------------------------------------------

    # ---------------------------------------------------
    # Slash commands

    att = SlashCommandGroup("a", "Automatic Attack Commands")

    @att.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select)
    @option("roll", description="Roll or Macro Roll", autocomplete=a_macro_select)
    @option("vs", description="Target Attribute", autocomplete=get_attributes)
    @option("attack_modifier", description="Modifier to the macro (defaults to +)", required=False)
    @option("target_modifier", description="Modifier to the target's dc (defaults to +)", required=False)
    async def attack(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        roll: str,
        vs: str,
        attack_modifier: str = "",
        target_modifier: str = "",
    ):
        logging.info("attack_cog attack")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        try:
            await ctx.response.defer()
            Automation = await get_automation(ctx, engine=engine)
            output_string = await Automation.attack(character, target, roll, vs, attack_modifier, target_modifier)
            await ctx.send_followup(output_string)
        except Exception as e:
            logging.warning(f"attack_cog attack {e}")
            report = ErrorReport(ctx, "/a attack", e, self.bot)
            await report.report()
            await ctx.send_followup(
                "Error. Ensure that you selected valid targets and attack rolls.  Ensure that if "
                "you used a non-macro roll that it conforms tothe XdY+Z format without any "
                "labels."
            )
        await engine.dispose()

    @att.command(description="Saving Throw")
    @option("character", description="Character forcing the save", autocomplete=character_select_gm)
    @option("target", description="Saving Character", autocomplete=a_save_target_custom)
    @option("save", description="Save", autocomplete=save_select)
    @option("modifier", description="Modifier to the macro (defaults to +)", required=False)
    async def save(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        save: str,
        dc: int = None,
        modifier: str = "",
    ):
        logging.info("attack_cog save")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        try:
            Automation = await get_automation(ctx, engine=engine)
            output_string = await Automation.save(character, target, save, dc, modifier)
            await ctx.send_followup(output_string)
        except Exception as e:
            logging.warning(f"attack_cog save {e}")
            report = ErrorReport(ctx, "/a save", e, self.bot)
            await report.report()
            await ctx.send_followup("Error. Ensure that you selected valid targets and saves.")
        await engine.dispose()

    @att.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select)
    @option("user_roll_str", description="Roll or Macro Roll", autocomplete=a_macro_select)
    @option("modifier", description="Roll Modifer", default="", type=str)
    @option("healing", description="Apply as Healing?", default=False, type=bool)
    @option("damage_type", description="Damage Type", autocomplete=dmg_type, required=False)
    async def damage(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        user_roll_str: str,
        modifier: str = "",
        healing: bool = False,
        damage_type: str = "",
    ):
        logging.info("attack_cog damage")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        try:
            Automation = await get_automation(ctx, engine=engine)
            output_string = await Automation.damage(
                self.bot, character, target, user_roll_str, modifier, healing, damage_type
            )
            await ctx.send_followup(output_string)
        except Exception as e:
            logging.warning(f"attack_cog damage {e}")
            report = ErrorReport(ctx, "/a damage", e, self.bot)
            await report.report()
            await ctx.send_followup("Error. Ensure that your input was a valid dice roll or value.")
        await engine.dispose()

    @att.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select)
    @option("attack", description="Roll or Macro Roll", autocomplete=a_macro_select)
    @option("attack_modifier", description="Attack Modifier", required=False)
    @option("target_modifier", description="Target Modifier", required=False)
    @option("damage_modifier", description="Flat Bonus or Penalty to Damage", required=False)
    async def auto(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        attack: str,
        attack_modifer: str = "",
        target_modifier: str = "",
        damage_modifier: str = "",
    ):
        logging.info("attack_cog auto")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        try:
            Automation = await get_automation(ctx, engine=engine)
            output_string = await Automation.auto(
                self.bot, character, target, attack, attack_modifer, target_modifier, damage_modifier
            )
            await ctx.send_followup(output_string)
        except Exception as e:
            logging.warning(f"attack_cog auto {e}")
            report = ErrorReport(ctx, "/a auto", e, self.bot)
            await report.report()
            await ctx.send_followup("Error. Ensure that you selected a valid target and attack.")
        await engine.dispose()

    @att.command(description="Cast a Spell (EPF Only)")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select)
    @option("spell", description="Roll or Macro Roll", autocomplete=spell_list)
    @option("level", description="Spell Level", autocomplete=spell_level)
    @option("attack_modifier", description="Attack Modifier", required=False)
    @option("target_modifier", description="Target Modifier", required=False)
    @option("damage_modifier", description="Flat Bonus or Penalty to Damage", required=False)
    async def cast(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        spell: str,
        level: int,
        attack_modifer: str = "",
        target_modifier: str = "",
        damage_modifier: str = "",
    ):
        logging.info("attack_cog cast")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        try:
            Automation = await get_automation(ctx, engine=engine)
            output_string = await Automation.cast(
                self.bot, character, target, spell, level, attack_modifer, target_modifier, damage_modifier
            )
            await ctx.send_followup(output_string)
        except Exception as e:
            logging.warning(f"attack_cog cast {e}")
            report = ErrorReport(ctx, "/a cast", e, self.bot)
            await report.report()
            await ctx.send_followup("Error.  Ensure that you selected a valid spell, target and level.")
        await engine.dispose()


def setup(bot):
    bot.add_cog(AutomationCog(bot))
