# automation_cog.py

import logging

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from auto_complete import character_select, character_select_gm, a_macro_select, get_attributes, a_save_target_custom, \
    save_select
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
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
        # bughunt code
        logging.info("attack_cog attack")

        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        await ctx.response.defer()
        Automation = await get_automation(ctx, engine=engine)
        output_string = await Automation.attack(character, target, roll, vs, attack_modifier, target_modifier)
        await ctx.send_followup(output_string)
        await engine.dispose()

    @att.command(description="Saving Throw")
    @option("character", description="Character forcing the sae", autocomplete=character_select_gm)
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
        # bughunt code
        logging.info("attack_cog save")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()

        Automation = await get_automation(ctx, engine=engine)
        output_string = await Automation.save(character, target, save, dc, modifier)
        await ctx.send_followup(output_string)

        await engine.dispose()

    @att.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select)
    @option("user_roll_str", description="Roll or Macro Roll", autocomplete=a_macro_select)
    @option("modifier", description="Roll Modifer", default='', type=str)
    @option("healing", description="Apply as Healing?", default=False, type=bool)
    async def damage(
            self,
            ctx: discord.ApplicationContext,
            character: str,
            target: str,
            user_roll_str: str,
            modifier: str = '',
            healing: bool = False,
    ):
        # bughunt code
        logging.info(f"attack_cog damage")

        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        Automation = await get_automation(ctx, engine=self.engine)
        output_string = await Automation.damage(self.bot, character, target, user_roll_str, modifier, healing)
        await ctx.send_followup(output_string)
        await engine.dispose()


def setup(bot):
    bot.add_cog(AutomationCog(bot))