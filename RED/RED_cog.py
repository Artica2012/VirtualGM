# pf2_cog.py
# For slash commands specific to pathfinder 2e and EPF
# system specific module

import logging

import discord
import sqlalchemy.exc
from discord.commands import SlashCommandGroup, option
from discord.ext import commands

import RED.RED_GSHEET_Importer
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.Util_Getter import get_utilities
from utils.utils import get_guild


class REDCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    red = SlashCommandGroup("red", "CyberpunkRED Specific Commands")

    @red.command(description="Import Character")
    @option("name", description="Character Name", required=True)
    # @option("pathbuilder_id", description="Pathbuilder Export ID")
    @option("url", description="Public Google Sheet URL", required=True)
    async def import_character(self, ctx: discord.ApplicationContext, name: str, url: str, image: str = None):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        response = False
        success = discord.Embed(
            title=name.title(),
            fields=[discord.EmbedField(name="Success", value="Successfully Imported")],
            color=discord.Color.dark_gold(),
        )
        if url is not None:
            try:
                guild = await get_guild(ctx, None)
                if guild.system == "RED":
                    response = await RED.RED_GSHEET_Importer.red_g_sheet_import(ctx, name, url, image=image)
                    Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                    await Tracker_Model.update_pinned_tracker()
                else:
                    response = False
                if response:
                    Character_Model = await get_character(name, ctx, engine=engine)
                    success.set_thumbnail(url=Character_Model.pic)
                    await ctx.send_followup(embed=success)
                else:
                    await ctx.send_followup("Error importing character.")
            except sqlalchemy.exc.NoResultFound:
                await ctx.send_followup(
                    "No active tracker set up in this channel. Please make sure that you are in the "
                    "correct channel before trying again."
                )
            except Exception as e:
                await ctx.send_followup("Error importing character")
                logging.info(f"pb_import: {e}")
                report = ErrorReport(ctx, "g-sheet import", f"{e} - {url}", self.bot)
                await report.report()
        try:
            logging.info("Writing to Vault")
            guild = await get_guild(ctx, None)
            Character = await get_character(name, ctx, guild=guild, engine=engine)
            if Character.player:
                Utilities = await get_utilities(ctx, guild=guild, engine=engine)
                await Utilities.add_to_vault(name)
        except Exception as e:
            logging.warning(f"pb_import: {e}")
            # report = ErrorReport(ctx, "write to vault", f"{e} - {url}", self.bot)
            # await report.report()


def setup(bot):
    bot.add_cog(REDCog(bot))
