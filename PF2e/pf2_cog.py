# pf2_cog.py
# For slash commands specific to pathfinder 2e and EPF
# system specific module

import logging

import discord
import sqlalchemy.exc
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from discord.ext.pages import Paginator
import EPF.EPF_GSHEET_Importer
import database_operations
import initiative
import utils.utils
from EPF.EPF_Character import pb_import
from EPF.EPF_NPC_Importer import epf_npc_lookup
from PF2e.NPC_importer import npc_lookup
from PF2e.pathbuilder_importer import pathbuilder_import
from PF2e.pf2_db_lookup import WandererLookup
from auto_complete import character_select_gm, attacks, stats, dmg_type, npc_search
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA, DATABASE
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.Util_Getter import get_utilities
from utils.utils import get_guild
from EPF.Wanderer_Import import WandererImporter, get_WandeerImporter


class PF2Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    pf2 = SlashCommandGroup("pf2", "Pathfinder 2nd Edition Specific Commands")

    @pf2.command(description="Pathbuilder Import")
    @option("name", description="Character Name", required=True)
    @option("pathbuilder_id", description="Pathbuilder Export ID")
    @option("url", description="Public Google Sheet URL")
    @option("wanderer", description="Wanderer's Guide Export File", required=False)
    async def import_character(
        self,
        ctx: discord.ApplicationContext,
        name: str,
        pathbuilder_id: int = None,
        url: str = None,
        wanderer: discord.Attachment = None,
        image: str = None,
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        response = False
        success = discord.Embed(
            title=name.title(),
            fields=[discord.EmbedField(name="Success", value="Successfully Imported")],
            color=discord.Color.dark_gold(),
        )
        if wanderer is not None:
            Wanderer = await get_WandeerImporter(ctx, name, wanderer, image=image)
            await Wanderer.import_character()
        elif pathbuilder_id is None and url is None:
            await ctx.send_followup("Error, Please input either the pathbuilder ID, or the G-sheet url.")
        elif pathbuilder_id is not None:
            try:
                guild = await initiative.get_guild(ctx, None)
                Tracker_Model = await get_tracker_model(ctx, self.bot, guild=guild, engine=engine)

                if guild.system == "PF2":
                    response = await pathbuilder_import(ctx, engine, self.bot, name, str(pathbuilder_id), image=image)
                    if type(response) == str:
                        success.clear_fields()
                        success.add_field(name="Success", value=response)
                        Character_Model = await get_character(name, ctx, engine=engine)
                        success.set_thumbnail(url=Character_Model.pic)
                        await ctx.send_followup(embed=success)
                        await Tracker_Model.update_pinned_tracker()
                    else:
                        await ctx.send_followup("Import Failed")
                elif guild.system == "EPF":
                    logging.info("Beginning PF2-Enhanced import")
                    response = await pb_import(ctx, engine, name, str(pathbuilder_id), guild=guild, image=image)
                    logging.info("Imported")
                    print(response)
                    if response:
                        Character_Model = await get_character(name, ctx, engine=engine)
                        success.set_thumbnail(url=Character_Model.pic)
                        await ctx.send_followup(embed=success)
                        await Tracker_Model.update_pinned_tracker()
                        logging.info("Import Successful")
                    else:
                        await ctx.send_followup("Import Failed")
                else:
                    await ctx.send_followup(
                        "System not assigned as Pathfinder 2e. Please ensure that the correct system was set at table"
                        " setup"
                    )
            except sqlalchemy.exc.NoResultFound:
                await ctx.send_followup(
                    "No active tracker set up in this channel. Please make sure that you are in the "
                    "correct channel before trying again."
                )
            except Exception as e:
                await ctx.send_followup("Error importing character")
                logging.info(f"pb_import: {e}")
                report = ErrorReport(ctx, "pb_import", f"{e} - {pathbuilder_id}", self.bot)
                await report.report()

        elif url is not None:
            try:
                guild = await get_guild(ctx, None)
                Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                if guild.system == "EPF":
                    response = await EPF.EPF_GSHEET_Importer.epf_g_sheet_import(ctx, name, url, image=image)
                else:
                    response = False
                if response:
                    Character_Model = await get_character(name, ctx, engine=engine)
                    success.set_thumbnail(url=Character_Model.pic)
                    await ctx.send_followup(embed=success)
                    await Tracker_Model.update_pinned_tracker()
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
            if Character.player == True:
                Utilities = await get_utilities(ctx, guild=guild, engine=engine)
                await Utilities.add_to_vault(name)
        except Exception as e:
            logging.warning(f"pb_import: {e}")
            report = ErrorReport(ctx, "write to vault", f"{e} - {url}", self.bot)
            await report.report()

    @pf2.command(description="NPC Import")
    @option("lookup", description="Search for a stat-block", autocomplete=npc_search)
    @option("elite_weak", choices=["weak", "elite"], required=False)
    async def add_npc(
        self,
        ctx: discord.ApplicationContext,
        name: str,
        lookup: str,
        elite_weak: str,
        number: int = 1,
        image: str = None,
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        response = False
        if number > 26:
            number = 26

        embeds = []
        success = discord.Embed(title=name.title(), fields=[], color=discord.Color.dark_gold())

        for x in range(0, number):
            if number > 1:
                modifier = f" {utils.utils.NPC_Iterator[x]}"
            else:
                modifier = ""
            try:
                if guild.system == "PF2":
                    response = await npc_lookup(
                        ctx, engine, lookup_engine, self.bot, f"{name}{modifier}", lookup, elite_weak, image=image
                    )

                    this_success = success.copy()
                    this_success.add_field(name=f"{name}{modifier}", value=f"{lookup} successfully added")
                    Character_Model = await get_character(f"{name}{modifier}", ctx, engine=engine)
                    # print(Character_Model.pic)
                    this_success.set_thumbnail(url=Character_Model.pic)
                    embeds.append(this_success)
                elif guild.system == "EPF":
                    response = await epf_npc_lookup(
                        ctx, engine, lookup_engine, self.bot, f"{name}{modifier}", lookup, elite_weak, image=image
                    )

                    this_success = success.copy()
                    this_success.add_field(name=f"{name}{modifier}", value=f"{lookup} successfully added")
                    Character_Model = await get_character(f"{name}{modifier}", ctx, engine=engine)
                    this_success.set_thumbnail(url=Character_Model.pic)
                    embeds.append(this_success)
            except Exception as e:
                await ctx.send_followup("Error importing character")
                logging.info(f"pb_import: {e}")
                report = ErrorReport(ctx, "add npc", f"{e} - {lookup}", self.bot)
                await report.report()
        await ctx.send_followup(embeds=embeds)
        Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine, guild=guild)
        await Tracker_Model.update_pinned_tracker()
        if not response:
            await ctx.send_followup("Import Failed")

    @pf2.command(description="Edit Attack")
    @option("character", description="Character to select", autocomplete=character_select_gm)
    @option("attack", description="Select Attack", autocomplete=attacks)
    @option("dmg_stat", description="Stat to use for damage", autocomplete=stats)
    @option("attk_stat", description="Stat to use for attack roll", autocomplete=stats)
    @option("dmg", description="Damage Type", autocomplete=dmg_type)
    @option("proficiency", description="Override the proficiency value for this weapon. 2 = Trained, 4 = Expert etc")
    async def edit_attack(
        self,
        ctx: discord.ApplicationContext,
        character,
        attack,
        dmg_stat=None,
        attk_stat=None,
        crit: str = None,
        dmg=None,
        proficiency: int = None,
    ):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        try:
            Utilities = await get_utilities(ctx, engine=engine)
            response = await Utilities.edit_attack(character, attack, dmg_stat, attk_stat, crit, dmg, proficiency)
        except Exception as e:
            await ctx.send_followup("Error importing character")
            logging.info(f"pb_import: {e}")
            report = ErrorReport(ctx, "edit attack", f"{e} - {character} {attack}", self.bot)
            await report.report()
        if response:
            await ctx.send_followup("Success")
        else:
            await ctx.send_followup("Failed")

    @pf2.command(description="Clone an attack and add bonus damage (EPF)")
    @option("character", description="Character to select", autocomplete=character_select_gm)
    @option("attack", description="Select Attack", autocomplete=attacks)
    @option("dmg_type", autocomplete=dmg_type)
    async def clone_attack(
        self, ctx: discord.ApplicationContext, character, attack, new_name: str, bonus_roll: str, dmg_type
    ):
        await ctx.response.defer(ephemeral=True)
        engine = database_operations.engine
        response = False

        try:
            Character_Model = await get_character(character, ctx, engine=engine)
            response = await Character_Model.clone_attack(attack, new_name, bonus_roll, dmg_type)
        except Exception as e:
            await ctx.send_followup("Error cloning attack")
            logging.info(f"clone attack: {e}")
            report = ErrorReport(ctx, "Clone attack", f"{e} - {character} {attack}", self.bot)
            await report.report()
        if response:
            await ctx.send_followup("Success")
        else:
            await ctx.send_followup("Failed")

    @pf2.command(description="Edit Character Resistances")
    @option("character", description="Character to select", autocomplete=character_select_gm)
    @option("element", autocomplete=dmg_type)
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

    @pf2.command(description="Pathfinder Lookup")
    # @option("category", description="category", required=True, choices=pf2_wanderer_lookup.endpoints.keys())
    @option("query", description="Lookup")
    @option("private", description="Keep Lookup private (True), or allow the world to see (False).")
    async def lookup(self, ctx: discord.ApplicationContext, query: str, private: bool = True):
        await ctx.response.defer(ephemeral=private)
        try:
            # Wanderer = pf2_wanderer_lookup.Wanderer(os.environ["WANDERER_CLIENT_ID"], os.environ["WANDERER_API_KEY"])
            # await ctx.send_followup(embeds=await Wanderer.wander(category, query=query))
            Lookup = WandererLookup()
            paginator = Paginator(pages=await Lookup.lookup(query))
            await paginator.respond(ctx.interaction, ephemeral=private)
        except Exception as e:
            await ctx.send_followup(
                (
                    "**WARNING: THERE IS A NEW LOOKUP DATABASE**\nPlease alert if there are issues \n\nLookup Failed."
                    " No Results."
                ),
                ephemeral=private,
            )
            logging.info(f"pf2_lookup {query}: {e}")
            report = ErrorReport(ctx, f"pf2_lookup_new {query}", e, self.bot)
            await report.report()


def setup(bot):
    bot.add_cog(PF2Cog(bot))
