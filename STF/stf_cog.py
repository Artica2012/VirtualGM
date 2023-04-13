# stf_cog.py
# For slash commands specific to pathfinder 2e and EPF
# system specific module

import logging

import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands

from STF.STF_GSHEET_IMPORTER import stf_g_sheet_import
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

    @stf.command(description="Starfinder Import")
    @option("name", description="Character Name", required=True)
    @option("url", description="Public Google Sheet URL")
    async def import_character(self, ctx: discord.ApplicationContext, name: str, url: str = None):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        response = False

        try:
            guild = await get_guild(ctx, None)
            if guild.system == "STF":
                response = await stf_g_sheet_import(ctx, name, url)
                Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                await Tracker_Model.update_pinned_tracker()
                await engine.dispose()
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
        await engine.dispose()


def setup(bot):
    bot.add_cog(STFCog(bot))
