# pf2_cog.py
# For slash commands specific to pathfinder 2e and EPF
# system specific module

import logging
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
import EPF.EPF_GSHEET_Importer
import initiative
from EPF.EPF_Character import pb_import, calculate
from EPF.EPF_NPC_Importer import epf_npc_lookup
from PF2e.NPC_importer import npc_lookup
from PF2e.pathbuilder_importer import pathbuilder_import
from auto_complete import character_select_gm, attacks, stats, dmg_type, npc_search
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA, DATABASE
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.Util_Getter import get_utilities
from utils.utils import get_guild


class PF2Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    pf2 = SlashCommandGroup("pf2", "Pathfinder 2nd Edition Specific Commands")

    @pf2.command(description="Pathbuilder Import")
    @option("name", description="Character Name", required=True)
    @option("pathbuilder_id", description="Pathbuilder Export ID")
    @option("url", description="Public Google Sheet URL")
    async def import_character(self, ctx: discord.ApplicationContext, name: str, pathbuilder_id: int, url: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer(ephemeral=True)
        if pathbuilder_id is None and url is None:
            await ctx.send_followup("Error, Please input either the pathbuilder ID, or the G-sheet url.")
        elif pathbuilder_id is not None:
            try:
                guild = await initiative.get_guild(ctx, None)
                Tracker_Model = await get_tracker_model(ctx, self.bot, guild=guild, engine=engine)

                if guild.system == "PF2":
                    response = await pathbuilder_import(ctx, engine, self.bot, name, str(pathbuilder_id))
                    if response:
                        await Tracker_Model.update_pinned_tracker()
                    else:
                        await ctx.send_followup("Import Failed")
                elif guild.system == "EPF":
                    logging.info("Beginning PF2-Enhanced import")
                    response = await pb_import(ctx, engine, name, str(pathbuilder_id), guild=guild)
                    logging.info("Imported")
                    if response:
                        await Tracker_Model.update_pinned_tracker()
                        await ctx.send_followup("Success")
                        logging.info("Import Successful")
                    else:
                        await ctx.send_followup("Import Failed")
                else:
                    await ctx.send_followup(
                        "System not assigned as Pathfinder 2e. Please ensure that the correct system was set at table"
                        " setup"
                    )
                await engine.dispose()
            except Exception as e:
                await ctx.send_followup("Error importing character")
                logging.info(f"pb_import: {e}")
                report = ErrorReport(ctx, "pb_import", f"{e} - {pathbuilder_id}", self.bot)
                await report.report()
                await engine.dispose()

        elif url is not None:
            try:
                guild = await get_guild(ctx, None)
                if guild.system == "EPF":
                    response = await EPF.EPF_GSHEET_Importer.epf_g_sheet_import(ctx, name, url)
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
                await engine.dispose()

    @pf2.command(description="NPC Import")
    @option("lookup", description="Search for a stat-block", autocomplete=npc_search)
    @option("elite_weak", choices=["weak", "elite"], required=False)
    async def add_npc(self, ctx: discord.ApplicationContext, name: str, lookup: str, elite_weak: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        response = False
        try:
            if guild.system == "PF2":
                response = await npc_lookup(ctx, engine, lookup_engine, self.bot, name, lookup, elite_weak)
            elif guild.system == "EPF":
                response = await epf_npc_lookup(ctx, engine, lookup_engine, self.bot, name, lookup, elite_weak)
        except Exception as e:
            await ctx.send_followup("Error importing character")
            logging.info(f"pb_import: {e}")
            report = ErrorReport(ctx, "add npc", f"{e} - {lookup}", self.bot)
            await report.report()

        if not response:
            await ctx.send_followup("Import Failed")
        await engine.dispose()

    @pf2.command(description="Edit Attack")
    @option("character", description="Character to select", autocomplete=character_select_gm)
    @option("attack", description="Select Attack", autocomplete=attacks)
    @option("dmg_stat", description="Stat to use for damage", autocomplete=stats)
    @option("attk_stat", description="Stat to use for attack roll", autocomplete=stats)
    @option("dmg", description="Damage Type", autocomplete=dmg_type)
    async def edit_attack(
        self,
        ctx: discord.ApplicationContext,
        character,
        attack,
        dmg_stat=None,
        attk_stat=None,
        crit: str = None,
        dmg=None,
    ):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        try:
            Utilities = await get_utilities(ctx, engine=engine)
            response = await Utilities.edit_attack(character, attack, dmg_stat, attk_stat, crit, dmg)
        except Exception as e:
            await ctx.send_followup("Error importing character")
            logging.info(f"pb_import: {e}")
            report = ErrorReport(ctx, "edit attack", f"{e} - {character} {attack}", self.bot)
            await report.report()
        if response:
            await ctx.send_followup("Success")
        else:
            await ctx.send_followup("Failed")
        await engine.dispose()

    @pf2.command(description="Edit Character Resistances")
    @option("character", description="Character to select", autocomplete=character_select_gm)
    @option("element", autocomplete=dmg_type)
    @option("resist_weak", choices=["Resistance", "Weakness", "Immunity"])
    async def resistances(self, ctx: discord.ApplicationContext, character, element, resist_weak, amount: int):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Character = await get_character(character, ctx, engine=engine)

        match resist_weak:
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
        await engine.dispose()


def setup(bot):
    bot.add_cog(PF2Cog(bot))
