# pf2_cog.py
# For slash commands specific to pathfinder 2e
# system specific module
import logging

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands

import initiative
from EPF.EPF_Character import pb_import, calculate
from PF2e.NPC_importer import npc_lookup
from PF2e.pathbuilder_importer import pathbuilder_import
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA, DATABASE
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.Tracker_Getter import get_tracker_model


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
            Tracker_Model = await get_tracker_model(ctx, self.bot, guild=guild, engine=engine)

            if guild.system == "PF2":
                response = await pathbuilder_import(ctx, engine, self.bot, name, str(pathbuilder_id))
                if response:
                    await Tracker_Model.update_pinned_tracker()
                    # await ctx.send_followup("Success")

                else:
                    await ctx.send_followup("Import Failed")
            elif guild.system == "EPF":
                logging.info("Beginning PF2-Enhanced import")
                response = await pb_import(ctx, engine, name, str(pathbuilder_id), guild=guild)
                logging.info("Imported")
                if response:
                    logging.info('Calculating')
                    await calculate(ctx, engine, name, guild=guild)
                    logging.info("Calculated")
                    await Tracker_Model.update_pinned_tracker()
                    await ctx.send_followup("Success")
                    logging.info("Import Successful")

                else:
                    await ctx.send_followup("Import Failed")
            else:
                await ctx.send_followup(
                    "System not assigned as Pathfinder 2e. Please ensure that the correct system was set at table setup"
                )
            await engine.dispose()
        except Exception as e:
            await ctx.send_followup("Error importing character")
            logging.info(f"pb_import: {e}")
            report = ErrorReport(ctx, "pb_import", f"{e} - {pathbuilder_id}", self.bot)
            await report.report()
            await engine.dispose()

    @pf2.command(description="Pathbuilder Import")
    @option("elite_weak", choices=["weak", "elite"], required=False)
    async def add_npc(self, ctx: discord.ApplicationContext, name: str, lookup: str, elite_weak: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        await ctx.response.defer()
        response = await npc_lookup(ctx, engine, lookup_engine, self.bot, name, lookup, elite_weak)
        if not response:
            await ctx.send_followup("Import Failed")
        await engine.dispose()


def setup(bot):
    bot.add_cog(PF2Cog(bot))
