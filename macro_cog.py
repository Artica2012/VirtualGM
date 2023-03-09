# macro_cog.py
# Macro-Roller Module for VirtualGM initiative Tracker
import asyncio
import os
import logging
import datetime
import inspect

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import d20

from database_models import Global, get_macro, get_tracker
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from auto_complete import character_select, macro_select, character_select_gm
from utils.Macro_Getter import get_macro_object
from utils.utils import get_guild
from utils.Char_Getter import get_character

# define global variables
from utils.parsing import ParseModifiers
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA


class MacroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    macro = SlashCommandGroup("macro", "Macro Commands")

    @macro.command(description="Create Macro")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    async def create(self, ctx: discord.ApplicationContext, character: str, macro_name: str, macro: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = await Macro_Model.create_macro(character, macro_name, macro)
        if result:
            await ctx.send_followup(f"Macro Created:\n{character}:{macro_name}: {macro}", ephemeral=True)
        else:
            await ctx.send_followup("Macro Creation Failed", ephemeral=True)
        await engine.dispose()

    @macro.command(description="Delete Macro")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    @option(
        "macro",
        description="Macro Name",
        autocomplete=macro_select,
    )
    async def remove(self, ctx: discord.ApplicationContext, character: str, macro: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = await Macro_Model.delete_macro(character, macro)
        if result:
            await ctx.send_followup("Macro Deleted Successfully")
        else:
            await ctx.send_followup("Delete Action Failed")
        await engine.dispose()

    @macro.command(description="Delete All Macros")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    async def remove_all(self, ctx: discord.ApplicationContext, character: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = await Macro_Model.delete_macro_all(character)
        if result:
            await ctx.send_followup("Macro Deleted Successfully")
        else:
            await ctx.send_followup("Delete Action Failed")
        await engine.dispose()

    @macro.command(description="Mass Import")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    @option("data", description="Import CSV data", required=True)
    async def bulk_create(self, ctx: discord.ApplicationContext, character: str, data: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = await Macro_Model.mass_add(character, data)
        if result:
            await ctx.send_followup("Macros Created Successfully")
        else:
            await ctx.send_followup("Action Failed")
        await engine.dispose()

    @macro.command(description="Display Macros")
    @option(
        "character",
        description="Character",
        autocomplete=character_select_gm,
    )
    async def show(self, ctx: discord.ApplicationContext, character: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        await ctx.send_followup(f"{character}: Macros", view=await Macro_Model.show(character), ephemeral=True)
        await engine.dispose()

    @commands.slash_command(name="m", description="Roll Macro")
    @option(
        "character",
        description="Character",
        autocomplete=character_select_gm,
    )
    @option(
        "macro",
        description="Macro Name",
        autocomplete=macro_select,
    )
    @option("modifier", description="Modifier to the macro (defaults to +)", required=False)
    @option("secret", choices=["Secret", "Open"])
    @option("dc", description="Number to which dice result will be compared", required=False)
    async def roll_macro_command(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        macro: str,
        modifier: str = "",
        dc: int = 0,
        secret: str = "Open",
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        Macro_Model = await get_macro_object(ctx, engine=engine, guild=guild)
        try:
            if secret == "Open":
                await ctx.send_followup(await Macro_Model.roll_macro(character, macro, dc, modifier, guild=guild))
            else:
                if guild.gm_tracker_channel is not None:
                    await ctx.send_followup(f"Secret Dice Rolled.{character}: {macro}")
                    await self.bot.get_channel(int(guild.gm_tracker_channel)).send(
                        f"Secret Roll:\n{await Macro_Model.roll_macro(character, macro, dc, modifier, guild=guild)}"
                    )
                else:
                    await ctx.send_followup("No GM Channel Initialized. Secret rolls not possible", ephemeral=True)
                    await ctx.channel.send(await Macro_Model.roll_macro(character, macro, dc, modifier, guild=guild))
        except Exception as e:
            logging.error(f"roll_macro: {e}")
            report = ErrorReport(ctx, "roll_macro", e, self.bot)
            await report.report()
            await ctx.send_followup("Macro Roll Failed")
        await engine.dispose()


def setup(bot):
    bot.add_cog(MacroCog(bot))
