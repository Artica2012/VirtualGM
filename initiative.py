# initiative.py
# Initiative Tracker Module

# imports
import asyncio
import logging

import d20
import discord
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from sqlalchemy import select
from sqlalchemy import true, false
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import auto_complete
from auto_complete import (
    character_select,
    character_select_gm,
    cc_select,
    npc_select,
    add_condition_select,
    initiative,
    character_select_con,
)
from database_models import Global, get_tracker
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import error_not_initialized, ErrorReport
from initiative_functions import edit_cc_interface
from time_keeping_functions import check_timekeeper
from utils import utils
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.Util_Getter import get_utilities
from utils.utils import gm_check, get_guild


#############################################################################
#############################################################################
# SLASH COMMANDS
# The Initiative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def time_check_ac(self, ctx: discord.AutocompleteContext):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        if await check_timekeeper(ctx, engine):
            # await engine.dispose()
            return ["Round", "Minute", "Hour", "Day"]
        else:
            # await engine.dispose()
            return ["Round"]

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Slash commands

    i = SlashCommandGroup("i", "Initiative Tracker")
    char = SlashCommandGroup("char", "Character Commands")
    cc = SlashCommandGroup("cc", "Conditions and Counters")

    @char.command(
        description="Add PC on NPC",
        # guild_ids=[GUILD]
    )
    @option("name", description="Character Name", input_type=str)
    @option("hp", description="Total HP", input_type=str)
    @option("player", description="Player or NPC", choices=["player", "npc"], input_type=str)
    @option("initiative", description="Initiative Roll (XdY+Z)", required=True, input_type=str)
    @option("image", description="Link to character portrait.")
    async def add(
        self, ctx: discord.ApplicationContext, name: str, hp: str, player: str, initiative: str, image: str = None
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        player_bool = False
        if player == "player":
            player_bool = True
        elif player == "npc":
            player_bool = False

        Utilities = await get_utilities(ctx, engine=engine)
        try:
            hp = d20.roll(f"{hp}").total
            response = await Utilities.add_character(self.bot, name, hp, player_bool, initiative, image=image)
        except Exception as e:
            logging.warning(f"char add {e}")
            report = ErrorReport(ctx, "/char add", e, self.bot)
            await report.report()

        if response:
            success = discord.Embed(
                title=name.title(),
                fields=[discord.EmbedField(name="Success", value="Successfully Imported")],
                color=discord.Color.dark_gold(),
            )
            try:
                Character_Model = await get_character(name, ctx, engine=engine)
                success.set_thumbnail(url=Character_Model.pic)
            except AttributeError:
                pass
            await ctx.respond(embed=success)
            Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
            await Tracker_Model.update_pinned_tracker()
            if player_bool:
                await Utilities.add_to_vault(name)
        else:
            await ctx.respond("Error Adding Character", ephemeral=True)

    @char.command(description="Edit PC on NPC")
    @option(
        "name",
        description="Character Name",
        input_type=str,
        autocomplete=character_select_gm,
    )
    @option("hp", description="Total HP", input_type=int, required=False)
    @option("initiative", description="Initiative Roll (XdY+Z)", required=False, input_type=str)
    @option("active", description="Active State", required=False, input_type=bool)
    @option("image", description="Link to character portrait.")
    async def edit(
        self,
        ctx: discord.ApplicationContext,
        name: str,
        hp: int = None,
        initiative: str = None,
        active: bool = None,
        player: discord.User = None,
        image: str = "",
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        guild = await get_guild(ctx, None)
        response = False

        if await auto_complete.hard_lock(ctx, name):
            try:
                Character_Model = await get_character(name, ctx, guild=guild, engine=engine)
                response = await Character_Model.edit_character(name, hp, initiative, active, player, image, self.bot)
            except Exception as e:
                logging.warning(f"char edit {e}")
                report = ErrorReport(ctx, "/char edit", e, self.bot)
                await report.report()

            if not response:
                await ctx.respond("Error Editing Character", ephemeral=True)
            else:
                Tracker_Model = await get_tracker_model(ctx, self.bot, guild=guild, engine=engine)
                await Tracker_Model.update_pinned_tracker()
        else:
            await ctx.respond("You do not have the appropriate permissions to edit this character.")

    @char.command(description="Duplicate Character")
    @option(
        "name",
        description="Character Name",
        input_type=str,
        autocomplete=character_select_gm,
    )
    @option("new_name", description="Name for the new NPC", input_type=str, required=True)
    async def copy(self, ctx: discord.ApplicationContext, name: str, new_name: str, number: int = 1):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer(ephemeral=True)
        response = False

        if number > 26:
            number = 26
        embeds = []
        success = discord.Embed(title=name.title(), fields=[], color=discord.Color.dark_gold())
        Utilities = await get_utilities(ctx, engine=engine)
        for x in range(0, number):
            if number > 1:
                modifier = f" {utils.NPC_Iterator[x]}"
            else:
                modifier = ""
            try:
                response = await Utilities.copy_character(name, f"{new_name}{modifier}")
                if response:
                    this_success = success.copy()
                    this_success.add_field(name=f"{name}{modifier}", value=f"Successfully copied.")
                    Character_Model = await get_character(f"{new_name}{modifier}", ctx, engine=engine)
                    if Character_Model.player:
                        await Utilities.add_to_vault(Character_Model.char_name)
                    this_success.set_thumbnail(url=Character_Model.pic)
                    embeds.append(this_success)
                else:
                    raise Exception
            except Exception as e:
                logging.warning(f"char copy {e}")
                report = ErrorReport(ctx, "/char copy", e, self.bot)
                await report.report()
                failure = discord.Embed(title=name.title(), description="Copy Failed", color=discord.Color.red())
                embeds.append(failure)

        await ctx.send_followup(embeds=embeds)
        Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
        await Tracker_Model.update_pinned_tracker()

    @char.command(description="Delete NPC")
    @option(
        "name",
        description="Character Name",
        input_type=str,
        autocomplete=npc_select,
    )
    async def delete(self, ctx: discord.ApplicationContext, name: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer(ephemeral=True)
        if await auto_complete.hard_lock(ctx, name):
            try:
                guild = await get_guild(ctx, None)

                if name == guild.saved_order:
                    await ctx.send_followup(
                        f"Please wait until {name} is not the active character in initiative before deleting it.",
                        ephemeral=True,
                    )
                else:
                    result = False
                    try:
                        Utilities = await get_utilities(ctx, guild=guild, engine=engine)
                        result = await Utilities.delete_character(character=name)
                    except Exception as e:
                        logging.warning(f"char delete {e}")
                        report = ErrorReport(ctx, "/char delete", e, self.bot)
                        await report.report()
                    if result:
                        await ctx.send_followup(f"{name} deleted", ephemeral=True)
                        Tracker_Model = await get_tracker_model(ctx, self.bot, guild=guild, engine=engine)
                        await Tracker_Model.update_pinned_tracker()
                    else:
                        await ctx.send_followup("Delete Operation Failed", ephemeral=True)
            except NoResultFound:
                await ctx.respond(error_not_initialized, ephemeral=True)
                return False
            except IndexError:
                await ctx.respond("Ensure that you have added characters to the initiative list.")
            except Exception:
                await ctx.respond("Failed")
        else:
            await ctx.respond("You do not have the appropriate permissions to delete this character.")

    @char.command(description="Display Character Sheet")
    @option(
        "name",
        description="Character Name",
        input_type=str,
        autocomplete=character_select_gm,
    )
    async def sheet(self, ctx: discord.ApplicationContext, name: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        if await auto_complete.hard_lock(ctx, name):
            try:
                Character_Model = await get_character(name, ctx, engine=engine)
                embed = await Character_Model.get_char_sheet(self.bot)
                await ctx.send_followup(embeds=embed)
            except Exception as e:
                logging.warning(f"char sheet {e}")
                report = ErrorReport(ctx, "/char sheet", e, self.bot)
                await report.report()
                await ctx.send_followup("Error displaying character sheet. Ensure valid character.")
        else:
            await ctx.send_followup("You do not have the appropriate permissions to view this character.")

    @i.command(
        description="Manage Initiative",
    )
    @discord.default_permissions(manage_messages=True)
    @option("mode", choices=["start", "stop", "delete character", "reroll initiative"], required=True)
    @option("character", description="Character to delete", required=False)
    async def manage(self, ctx: discord.ApplicationContext, mode: str, character: str = ""):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        try:
            guild = await get_guild(ctx, None)
            Tracker_Model = await get_tracker_model(ctx, self.bot, guild=guild, engine=engine)
            if not await gm_check(ctx, engine):
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            else:
                if mode == "start":
                    await ctx.response.defer()
                    await Tracker_Model.next()

                elif mode == "stop":  # Stop initiative
                    await ctx.response.defer()
                    await Tracker_Model.end()

                    await ctx.send_followup("Initiative Ended.")
                elif mode == "delete character":
                    if character == guild.saved_order:
                        await ctx.respond(
                            (
                                f"Please wait until {character} is not the active character in initiative before "
                                "deleting it."
                            ),
                            ephemeral=True,
                        )
                    else:
                        await ctx.response.defer(ephemeral=True)
                        Utilities = await get_utilities(ctx, guild=guild, engine=engine)
                        result = await Utilities.delete_character(character)
                        if result:
                            await ctx.send_followup(f"{character} deleted", ephemeral=True)
                            await Tracker_Model.update()
                            await Tracker_Model.update_pinned_tracker()
                            try:
                                await Utilities.delete_from_vault(character)
                            except Exception:
                                pass
                        else:
                            await ctx.send_followup("Delete Operation Failed", ephemeral=True)
                elif mode == "reroll initiative":
                    await ctx.response.defer()
                    await Tracker_Model.reroll_init()

        except NoResultFound:
            await ctx.respond(error_not_initialized, ephemeral=True)
            return False
        except IndexError:
            await ctx.respond("Ensure that you have added characters to the initiative list.")
        except Exception as e:
            await ctx.respond("Failed")
            logging.warning(f"/i mange {e}")
            report = ErrorReport(ctx, "/i manage", e, self.bot)
            await report.report()

    @i.command(
        description="Advance Initiative",
    )
    async def next(self, ctx: discord.ApplicationContext):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        try:
            await ctx.response.defer()
            Tracker_Object = await get_tracker_model(ctx, self.bot, engine=engine)
            await Tracker_Object.next()

        except NoResultFound:
            await ctx.respond(error_not_initialized, ephemeral=True)
        except PermissionError:
            await ctx.message.delete()
        except Exception as e:
            await ctx.respond("Error", ephemeral=True)
            logging.warning(f"/i next: {e}")
            report = ErrorReport(ctx, "slash command /i next", e, self.bot)
            await report.report()

    @i.command(
        description="Set Init (Number or XdY+Z)",
    )
    @option(
        "character",
        description="Character to select",
        autocomplete=character_select_gm,
    )
    @option("initiative", autocomplete=initiative, description="Initiative")
    async def init(self, ctx: discord.ApplicationContext, character: str, initiative: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        guild = await get_guild(ctx, None)
        if character == guild.saved_order:
            await ctx.respond(
                (
                    f"Please wait until {character} is not the active character in initiative before "
                    "resetting its initiative."
                ),
                ephemeral=True,
            )
        else:
            try:
                model = await get_character(character, ctx, guild=guild, engine=engine)
                output = await model.set_init(initiative)
                await ctx.respond(output)
                Tracker_Object = await get_tracker_model(ctx, self.bot, engine=engine)
                await Tracker_Object.update_pinned_tracker()
            except Exception as e:
                await ctx.respond(f"Failed to set initiative for {character}.\n{e}", ephemeral=True)

    @i.command(
        description="Heal, Damage or add Temp HP",
    )
    @option("name", description="Character Name", autocomplete=character_select)
    @option("mode", choices=["Damage", "Heal", "Temporary HP"])
    async def hp(self, ctx: discord.ApplicationContext, name: str, mode: str, amount: int):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        try:
            model = await get_character(name, ctx, guild=guild, engine=engine)
            if mode == "Temporary HP":
                response = await model.add_thp(amount)
                if response:
                    await ctx.respond(f"{amount} Temporary HP added to {name}.")
            else:
                if mode == "Heal":
                    heal = True
                else:
                    heal = False
                response = await model.change_hp(amount, heal)
        except Exception as e:
            await ctx.respond("Error", ephemeral=True)
            logging.warning(f"/i hp: {e}")
            report = ErrorReport(ctx, "slash command /i hp", e, self.bot)
            await report.report()

        if not response:
            await ctx.respond("Failed", ephemeral=True)
        else:
            Tracker_Object = await get_tracker_model(ctx, self.bot, engine=engine, guild=guild)
            await Tracker_Object.update_pinned_tracker()

    @cc.command(
        description="Add conditions and counters",
    )
    @option("character", description="Character to select", autocomplete=character_select_con)
    @option("title", description="Name of Condition/Counter", autocomplete=add_condition_select)
    @option(
        "type",
        description="Condition = Always Dispalyed, Counter = Displayed on Turn Only",
        choices=["Condition", "Counter"],
    )
    @option("auto", description="Auto Decrement", choices=["Auto Decrement", "Static"])
    @option("unit", description="Unit of Time (if applicable)", autocomplete=time_check_ac)
    @option("flex", description="Function Varies depending on system", autocomplete=auto_complete.flex_ac)
    @option("data", description="Add functionality to condition (only for systems with a scripting language")
    @option(
        "linked_character",
        description="Character whose turn the condition decrements on.",
        autocomplete=character_select,
        required=False,
    )
    async def new(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        title: str,
        type: str,
        number: int = None,
        unit: str = "Round",
        auto: str = "Static",
        flex: str = "False",
        data: str = "",
        linked_character: str = None,
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        match flex:  # noqa
            case "Decrement at beginning of the Turn":
                flex_bool = True
            case "Decrement at end of the Turn":
                flex_bool = False
            case "True":
                flex_bool = True
            case "False":
                flex_bool = False
            case "Ends with Save":
                flex_bool = True
            case "Ends after set time":
                flex_bool = False
            case _:
                flex_bool = False

        if type == "Condition":
            counter_bool = False
        else:
            counter_bool = True
        if auto == "Auto Decrement":
            auto_bool = True
        else:
            auto_bool = False
        response = False

        success_string = f"Condition {title} added on:"
        embeds = []
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        if character == "All PCs":
            async with async_session() as session:
                char_result = await session.execute(select(Tracker.name).where(Tracker.player == true()))
                char_list = char_result.scalars().all()
        elif character == "All NPCs":
            async with async_session() as session:
                char_result = await session.execute(select(Tracker.name).where(Tracker.player == false()))
                char_list = char_result.scalars().all()
        else:
            char_list = [character]

        for char in char_list:
            try:
                model = await get_character(char, ctx, guild=guild, engine=engine)
                response = await model.set_cc(
                    title, counter_bool, number, unit, auto_bool, flex=flex_bool, data=data, target=linked_character
                )
                if response:
                    success = discord.Embed(
                        title=model.char_name.title(),
                        fields=[
                            discord.EmbedField(
                                name="Success", value=f"{title} {number if number != None else ''} added."
                            )
                        ],
                        color=discord.Color.blurple(),
                    )
                    success.set_thumbnail(url=model.pic)
                    embeds.append(success)
                    success_string += f"\n{char}"
                else:
                    raise KeyError

            except Exception as e:
                failure = discord.Embed(
                    title=char.title(),
                    fields=[
                        discord.EmbedField(
                            name="Failure", value=f"{title} {number if number != None else ''} not added."
                        )
                    ],
                    color=discord.Color.greyple(),
                )
                embeds.append(failure)
                logging.warning(f"/cc new: {e}")
                report = ErrorReport(ctx, f"slash command /cc new {char}", e, self.bot)
                await report.report()

        await ctx.send_followup(embeds=embeds)
        Tracker_Object = await get_tracker_model(ctx, self.bot, engine=engine, guild=guild)
        await Tracker_Object.update_pinned_tracker()

    @cc.command(
        description="Edit or remove conditions and counters",
    )
    @option("mode", choices=["edit", "delete"])
    @option("character", description="Character to select", autocomplete=character_select)
    @option("condition", description="Condition", autocomplete=cc_select)
    @option("value", description="Value (optional)", required=False)
    async def modify(
        self, ctx: discord.ApplicationContext, mode: str, character: str, condition: str, value: int = None
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer(ephemeral=True)
        Character_Model = await get_character(character, ctx, engine=engine)
        try:
            if mode == "delete":
                result = await Character_Model.delete_cc(condition)
                if result:
                    await ctx.send_followup("Successful Delete", ephemeral=True)
                    await ctx.send(f"{condition} on {character} deleted.")
            elif mode == "edit":
                if value is not None:
                    result = await Character_Model.edit_cc(condition, value)
                    if result:
                        await ctx.send_followup(f"{condition} on {character} updated to {value}.")
                    else:
                        await ctx.send_followup("Error")
                else:
                    output = await edit_cc_interface(ctx, engine, character, condition, self.bot)
                    if output[0] is not None:
                        await ctx.send_followup(output[0], view=output[1], ephemeral=True)
                    else:
                        await ctx.send_followup("Error")
            else:
                await ctx.send_followup("Invalid Input", ephemeral=True)

            Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
            await Tracker_Model.update_pinned_tracker()
        except Exception as e:
            await ctx.send_followup("Error", ephemeral=True)
            logging.warning(f"/cc modify: {e}")
            report = ErrorReport(ctx, "slash command /cc modify", e, self.bot)
            await report.report()


def setup(bot):
    bot.add_cog(InitiativeCog(bot))
