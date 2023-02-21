# attack_cog.py

import datetime
import os
import logging

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import or_, select, false
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import D4e.d4e_functions
import PF2e.pf2_functions
import auto_complete
import d20
import initiative
from database_models import Global, get_macro, get_tracker, get_condition
from database_operations import get_asyncio_db_engine
from auto_complete import character_select, character_select_gm, a_macro_select

# define global variables

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# UTILITY FUNCTIONS

# Checks to see if the user of the slash command is the GM, returns a boolean


class AttackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_attributes(self, ctx: discord.AutocompleteContext):
        # bughunt code
        logging.info(f"{datetime.datetime.now()} - attack_cog get_attributes")
        try:
            engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            async with async_session() as session:
                result = await session.execute(
                    select(Global).where(
                        or_(
                            Global.tracker_channel == ctx.interaction.channel_id,
                            Global.gm_tracker_channel == ctx.interaction.channel_id,
                        )
                    )
                )
                guild = result.scalars().one()
            await engine.dispose()
            if guild.system == "PF2":
                return PF2e.pf2_functions.PF2_attributes
            elif guild.system == "D4e":
                return D4e.d4e_functions.D4e_attributes
            else:
                try:
                    # This should currently be inaccessible,
                    # but it might be useful for a future build your own system thing
                    target = ctx.options["target"]
                    Tracker = await get_tracker(ctx, engine, id=guild.id)
                    Condition = await get_condition(ctx, engine, id=guild.id)
                    async with async_session() as session:
                        result = await session.execute(select(Tracker).where(Tracker.name == target))
                        tar_char = result.scalars().one()
                    async with async_session() as session:
                        result = await session.execute(
                            select(Condition.title)
                            .where(Condition.character_id == tar_char.id)
                            .where(Condition.visible == false())
                        )
                        invisible_conditions = result.scalars().all()
                    return invisible_conditions
                except Exception:
                    return []
        except Exception as e:
            logging.warning(f"get_attributes, {e}")
            return []

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
        logging.info(f"{datetime.datetime.now()} - attack_cog attack")

        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        await ctx.response.defer()
        guild = await initiative.get_guild(ctx, None)
        if not guild.system:
            await ctx.respond("No system set, command inactive.")
            return

        if guild.system == "PF2":
            # PF2 specific code
            try:
                output_string = await PF2e.pf2_functions.attack(
                    ctx, engine, self.bot, character, target, roll, vs, attack_modifier, target_modifier
                )
            except Exception:
                Tracker = await get_tracker(ctx, engine, id=guild.id)
                Macro = await get_macro(ctx, engine, id=guild.id)

                async with async_session() as session:
                    result = await session.execute(select(Tracker).where(Tracker.name == character))
                    char = result.scalars().one()

                async with async_session() as session:
                    result = await session.execute(
                        select(Macro.macro).where(Macro.character_id == char.id).where(Macro.name == roll)
                    )
                    macro_roll = result.scalars().one()
                output_string = await PF2e.pf2_functions.attack(
                    ctx, engine, self.bot, character, target, macro_roll, vs, attack_modifier, target_modifier
                )

        elif guild.system == "D4e":
            # D4e specific code
            try:
                output_string = await D4e.d4e_functions.attack(
                    ctx, engine, self.bot, character, target, roll, vs, attack_modifier, target_modifier
                )
            except Exception:
                Tracker = await get_tracker(ctx, engine, id=guild.id)
                Macro = await get_macro(ctx, engine, id=guild.id)

                async with async_session() as session:
                    result = await session.execute(select(Tracker).where(Tracker.name == character))
                    char = result.scalars().one()

                async with async_session() as session:
                    result = await session.execute(
                        select(Macro.macro).where(Macro.character_id == char.id).where(Macro.name == roll)
                    )
                    macro_roll = result.scalars().one()
                output_string = await D4e.d4e_functions.attack(
                    ctx, engine, self.bot, character, target, macro_roll, vs, attack_modifier, target_modifier
                )

        else:
            output_string = "Error"
        await ctx.send_followup(output_string)
        await engine.dispose()

    @att.command(description="Saving Throw")
    @option("character", description="Character forcing the sae", autocomplete=character_select_gm)
    @option("target", description="Saving Character", autocomplete=character_select)
    @option("save", description="Save", autocomplete=auto_complete.save_select)
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
        logging.info(f"{datetime.datetime.now()} - attack_cog save")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        guild = await initiative.get_guild(ctx, None)
        if not guild.system:
            await ctx.respond("No system set, command inactive.")
            return
        # PF2 specific code
        if guild.system == "PF2":
            output_string = await PF2e.pf2_functions.save(ctx, engine, self.bot, character, target, save, dc, modifier)
            await ctx.send_followup(output_string)
        elif guild.system == "D4e":
            await ctx.send_followup(
                "Please use `/d4e save` for D&D 4e save functionality, or manually roll the save with `/r`"
            )

    @att.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select)
    @option("user_roll_str", description="Roll or Macro Roll", autocomplete=a_macro_select)
    @option("healing", description="Apply as Healing?", default=False, type=bool)
    async def damage(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        user_roll_str: str,
        healing: bool = False,
    ):
        # bughunt code
        logging.info(f"{datetime.datetime.now()} - attack_cog damage")

        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        await ctx.response.defer()
        async with async_session() as session:
            result = await session.execute(
                select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id,
                    )
                )
            )
            guild = result.scalars().one()
        if not guild.system:
            await ctx.respond("No system set, command inactive.")
            return

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Macro = await get_macro(ctx, engine, id=guild.id)

        # Rolls
        try:
            roll_result: d20.RollResult = d20.roll(user_roll_str)
            output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
        except Exception:
            try:
                async with async_session() as session:
                    result = await session.execute(select(Tracker).where(Tracker.name == character))
                    char = result.scalars().one()

                async with async_session() as session:
                    result = await session.execute(
                        select(Macro.macro).where(Macro.character_id == char.id).where(Macro.name == user_roll_str)
                    )
                    macro_roll = result.scalars().one()
                roll_result = d20.roll(macro_roll)
                output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
            except: # Error handling in case that a non-macro string in input
                roll_result = d20.roll(0)
                output_string = "Error: Invalid Roll, Please try again."
        # Apply the results
        await ctx.send_followup(output_string)
        await initiative.change_hp(ctx, engine, self.bot, target, roll_result.total, healing, guild=guild)
        await initiative.update_pinned_tracker(ctx, engine, self.bot, guild=guild)
        await engine.dispose()


def setup(bot):
    bot.add_cog(AttackCog(bot))
