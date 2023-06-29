# pf2_cog.py
# For slash commands specific to pathfinder 2e and EPF
# system specific module

import logging

import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands

import RED.RED_GSHEET_Importer
from auto_complete import (
    character_select_gm,
    auto_macro_select,
    red_no_net_character_select_multi,
    red_net_character_select_multi,
    net_macro_select,
)
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.Automation_Getter import get_automation
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
    @option("player", description="Player or NPC", choices=["player", "npc"], input_type=str)
    async def import_character(
        self, ctx: discord.ApplicationContext, name: str, url: str, player: str, image: str = None
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        response = False
        player_bool = False
        if player == "player":
            player_bool = True
        elif player == "npc":
            player_bool = False

        success = discord.Embed(
            title=name.title(),
            fields=[discord.EmbedField(name="Success", value="Successfully Imported")],
            color=discord.Color.dark_gold(),
        )
        if url is not None:
            # try:
            guild = await get_guild(ctx, None)
            if guild.system == "RED":
                response = await RED.RED_GSHEET_Importer.red_g_sheet_import(ctx, name, url, player_bool, image=image)
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
            # except NoResultFound:
            #     await ctx.send_followup(
            #         "No active tracker set up in this channel. Please make sure that you are in the "
            #         "correct channel before trying again."
            #     )
            # except Exception as e:
            #     await ctx.send_followup("Error importing character")
            #     logging.info(f"pb_import: {e}")
            #     report = ErrorReport(ctx, "g-sheet import", f"{e} - {url}", self.bot)
            #     await report.report()
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

    @red.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=red_no_net_character_select_multi)
    @option("attack", description="Roll or Macro Roll", autocomplete=auto_macro_select)
    @option("range", description="Range")
    @option("location", description="Location", choices=["Body", "Head"])
    @option("attack_modifier", description="Attack Modifier", required=False)
    @option("target_modifier", description="Target Modifier", required=False)
    @option("damage_modifier", description="Flat Bonus or Penalty to Damage", required=False)
    async def auto(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        attack: str,
        range: int,
        location="Body",
        attack_modifer: str = "",
        target_modifier: str = "",
        damage_modifier: str = "",
    ):
        logging.info("attack_cog auto")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        try:
            Automation = await get_automation(ctx, engine=engine)
            embeds = []
            if "," in target:
                multi_target = target.split(",")
                for char in multi_target:
                    try:
                        embeds.append(
                            await Automation.auto(
                                self.bot,
                                character,
                                char.strip(),
                                attack,
                                attack_modifer,
                                target_modifier,
                                damage_modifier,
                                multi=True,
                                range_value=range,
                                location=location,
                            )
                        )
                    except Exception:
                        embeds.append(
                            discord.Embed(title=char, fields=[discord.EmbedField(name=attack, value="Invalid Target")])
                        )
                Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                await Tracker_Model.update_pinned_tracker()
            else:
                embeds.append(
                    await Automation.auto(
                        self.bot,
                        character,
                        target,
                        attack,
                        attack_modifer,
                        target_modifier,
                        damage_modifier,
                        multi=False,
                        range_value=range,
                        location=location,
                    )
                )
            await ctx.send_followup(embeds=embeds)
        except KeyError:
            await ctx.send_followup("Error. Ensure that you have selected a valid attack.")
        except Exception as e:
            logging.warning(f"attack_cog auto {e}")
            report = ErrorReport(ctx, "/a auto", e, self.bot)
            await report.report()
            await ctx.send_followup("Error. Ensure that you selected a valid target and attack.")

    @red.command(description="NET Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=red_net_character_select_multi)
    @option("attack", description="NET Attack", autocomplete=net_macro_select)
    @option("attack_modifier", description="Attack Modifier", required=False)
    @option("target_modifier", description="Target Modifier", required=False)
    @option("damage_modifier", description="Flat Bonus or Penalty to Damage", required=False)
    async def net_auto(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        attack: str,
        attack_modifer: str = "",
        target_modifier: str = "",
        damage_modifier: str = "",
    ):
        logging.info("attack_cog auto")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        try:
            Automation = await get_automation(ctx, engine=engine)
            embeds = []
            if "," in target:
                multi_target = target.split(",")
                for char in multi_target:
                    try:
                        embeds.append(
                            await Automation.net_auto(
                                self.bot,
                                character,
                                char.strip(),
                                attack,
                                attack_modifer,
                                target_modifier,
                                damage_modifier,
                                multi=True,
                            )
                        )
                    except Exception:
                        embeds.append(
                            discord.Embed(title=char, fields=[discord.EmbedField(name=attack, value="Invalid Target")])
                        )
                Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                await Tracker_Model.update_pinned_tracker()
            else:
                embeds.append(
                    await Automation.net_auto(
                        self.bot,
                        character,
                        target,
                        attack,
                        attack_modifer,
                        target_modifier,
                        damage_modifier,
                        multi=False,
                    )
                )
            await ctx.send_followup(embeds=embeds)
        except KeyError:
            await ctx.send_followup("Error. Ensure that you have selected a valid attack.")
        except Exception as e:
            logging.warning(f"attack_cog auto {e}")
            report = ErrorReport(ctx, "/a auto", e, self.bot)
            await report.report()
            await ctx.send_followup("Error. Ensure that you selected a valid target and attack.")

    @red.command(description="Add or Remove Cover")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("amount", description="Cover HP")
    @option("remove", description="Remove Cover (True) or Add Cover (False)", choices=[True, False])
    async def cover(self, ctx, character, amount: int, remove: bool = False):
        await ctx.response.defer()
        try:
            Character_Model = await get_character(character, ctx)
            response = await Character_Model.set_cover(int(amount), remove=remove)
            if response:
                embed = discord.Embed(
                    title=Character_Model.char_name,
                    description=f"{'Cover Added' if not remove else 'Cover Removed'}",
                    color=discord.Color.dark_green(),
                )
                embed.set_thumbnail(url=Character_Model.pic)
            else:
                embed = discord.Embed(
                    title=Character_Model.char_name,
                    description="'Failed to Change Cover",
                    color=discord.Color.dark_red(),
                )
                embed.set_thumbnail(url=Character_Model.pic)
        except Exception:
            embed = discord.Embed(title="Error", description="'Failed to Change Cover", color=discord.Color.dark_red())
        await ctx.send_followup(embed=embed)
        Tracker_Model = await get_tracker_model(ctx, self.bot)
        await Tracker_Model.update_pinned_tracker()

    @red.command(description="Reset Armor to Undamaged Value")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    async def reset_armor(self, ctx: discord.ApplicationContext, character: str):
        await ctx.response.defer()
        try:
            Character_Model = await get_character(character, ctx)
            response = await Character_Model.ablate_armor(1, "body", reset=True)
            if response:
                embed = discord.Embed(
                    title=Character_Model.char_name,
                    description=f"{'Armor Reset'}",
                    color=discord.Color.dark_green(),
                )
                embed.set_thumbnail(url=Character_Model.pic)
            else:
                embed = discord.Embed(
                    title=Character_Model.char_name,
                    description="'Failed to Reset Armor",
                    color=discord.Color.dark_red(),
                )
                embed.set_thumbnail(url=Character_Model.pic)

        except Exception:
            embed = discord.Embed(title="Error", description="'Failed to Reset Arnir", color=discord.Color.dark_red())

        await ctx.send_followup(embed=embed)
        Tracker_Model = await get_tracker_model(ctx, self.bot)
        await Tracker_Model.update_pinned_tracker()


def setup(bot):
    bot.add_cog(REDCog(bot))
