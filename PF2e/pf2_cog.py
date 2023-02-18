# pf2_cog.py
# For slash commands specific to pathfinder 2e
# system specific module
import logging
import os

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from dotenv import load_dotenv

import initiative
from PF2e.NPC_importer import npc_lookup
from PF2e.pathbuilder_importer import pathbuilder_import
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from initiative import update_pinned_tracker

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


class PF2Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    pf2 = SlashCommandGroup("pf2", "Pathfinder 2nd Edition Specific Commands")

    @pf2.command(description="Pathbuilder Import")
    @option("pathbuilder_id", description="Pathbuilder Export ID", required=True)
    async def pb_import(self, ctx: discord.ApplicationContext, name: str, pathbuilder_id: int):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer(ephemeral=True)

        try:
            guild = await initiative.get_guild(ctx, None)

            if guild.system == "PF2":
                response = await pathbuilder_import(ctx, engine, self.bot, name, str(pathbuilder_id))
                if response:
                    await update_pinned_tracker(ctx, engine, self.bot)
                    # await ctx.send_followup("Success")

                else:
                    await ctx.send_followup("Import Failed")
            else:
                await ctx.send_followup(
                    "System not assigned as Pathfinder 2e. Please ensure that the correct system was set at table setup"
                )
        except Exception as e:
            await ctx.send_followup("Error importing character")
            logging.info(f"pb_import: {e}")
            report = ErrorReport(ctx, "pb_import", f"{e} - {pathbuilder_id}", self.bot)
            await report.report()

    @pf2.command(description="Pathbuilder Import")
    @option("elite_weak", choices=["weak", "elite"], required=False)
    async def add_npc(self, ctx: discord.ApplicationContext, name: str, lookup: str, elite_weak: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        await ctx.response.defer()
        response = await npc_lookup(ctx, engine, lookup_engine, self.bot, name, lookup, elite_weak)
        if not response:
            await ctx.send_followup("Import Failed")


def setup(bot):
    bot.add_cog(PF2Cog(bot))
