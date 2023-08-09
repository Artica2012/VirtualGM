# stf_cog.py
# For slash commands specific to pathfinder 2e and EPF
# system specific module

import logging

import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands

import auto_complete
import database_operations
from STF.STF_GSHEET_IMPORTER import stf_g_sheet_import
from auto_complete import character_select_gm
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.Util_Getter import get_utilities
from utils.utils import get_guild


class STFCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    stf = SlashCommandGroup("stf", "Pathfinder 2nd Edition Specific Commands")

    @stf.command(description="Restore Stamina with Resolve Point")
    @option(
        "name",
        description="Character Name",
        input_type=str,
        autocomplete=character_select_gm,
    )
    async def restore_stamina(self, ctx: discord.ApplicationContext, name: str):
        await ctx.response.defer()
        engine = database_operations.engine
        if await auto_complete.hard_lock(ctx, name):
            try:
                Character_Model = await get_character(name, ctx, engine=engine)
                result = await Character_Model.restore_stamina()
                if result:
                    await ctx.send_followup(
                        "Success.\n ```"
                        f"Current HP: {Character_Model.current_hp}/{Character_Model.max_hp}\n"
                        f"Current Stamina: {Character_Model.current_stamina}/"
                        f"{Character_Model.max_stamina}\n"
                        f"Resolve Points: {Character_Model.current_resolve}```"
                    )
                    Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                    await Tracker_Model.update_pinned_tracker()

                else:
                    await ctx.send_followup(
                        "Could not complete. Either you have no resolve Points or your stamina is full"
                    )
            except Exception as e:
                await ctx.send_followup("Error")
                logging.warning(f"stf restore stamina: {e}")
                report = ErrorReport(ctx, "write to vault", e, self.bot)
                await report.report()

    @stf.command(description="Starfinder Import")
    @option("name", description="Character Name", required=True)
    @option("url", description="Public Google Sheet URL")
    async def import_character(self, ctx: discord.ApplicationContext, name: str, url: str = None, image=None):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        response = False

        try:
            guild = await get_guild(ctx, None)
            if guild.system == "STF":
                response = await stf_g_sheet_import(ctx, name, url, image=image)
                Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                await Tracker_Model.update_pinned_tracker()

            else:
                response = False
            if response:
                await ctx.send_followup(f"{name} successfully imported.")
            else:
                await ctx.send_followup("Error importing character.")
        except Exception as e:
            await ctx.send_followup("Error importing character")
            logging.info(f"pb_import: {e}")
            report = ErrorReport(ctx, "g-sheet import", f"{e} - {url}", self.bot)
            await report.report()

        try:
            if response:
                logging.info("Writing to Vault")
                guild = await get_guild(ctx, None)
                Character = await get_character(name, ctx, guild=guild, engine=engine)
                if Character.player:
                    Utilities = await get_utilities(ctx, guild=guild, engine=engine)
                    await Utilities.add_to_vault(name)
        except Exception as e:
            logging.warning(f"stf_import: {e}")
            report = ErrorReport(ctx, "write to vault", f"{e} - {url}", self.bot)
            await report.report()

    @stf.command(description="Edit Character Resistances")
    @option("character", description="Character to select", autocomplete=character_select_gm)
    @option("element", autocomplete=auto_complete.dmg_type)
    @option("resist_weak", choices=["Resistance", "Weakness", "Immunity"])
    async def resistances(self, ctx: discord.ApplicationContext, character, element, resist_weak, amount: int):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Character = await get_character(character, ctx, engine=engine)

        match resist_weak:  # noqa
            case "Resistance":
                table = "r"
            case "Weakness":
                table = "w"
            case "Immunity":
                table = "i"
            case _:
                table = ""

        response = False
        try:
            response = await Character.update_resistance(table, element, amount)
        except Exception as e:
            await ctx.send_followup("Error importing character")
            logging.info(f"pb_import: {e}")
            report = ErrorReport(ctx, "edit resistances", f"{e} - {character} {element} {resist_weak}", self.bot)
            await report.report()
        if response:
            await ctx.send_followup(embeds=await Character.show_resistance())
        else:
            await ctx.send_followup("Failed")

    @stf.command(description="Edit Character Resistances")
    @option("mode", choices=["Start", "Stop", "Add_Starship"])
    async def starship(self, ctx: discord.ApplicationContext, mode: str, data: str = None):
        await ctx.response.defer()
        Tracker = await get_tracker_model(ctx, self.bot)
        await Tracker.start_starship_combat()


def setup(bot):
    bot.add_cog(STFCog(bot))
