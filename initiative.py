# initiative.py
# Initiative Tracker Module

# imports
import asyncio
import datetime
import logging
import inspect
import sys

import discord
import d20
import sqlalchemy as db
from discord import option, Interaction
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from sqlalchemy import or_, select, false, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.ddl import DropTable


from utils.Char_Getter import get_character
import auto_complete
import ui_components
from database_models import Global
from database_models import get_tracker, get_condition
from database_models import get_tracker_table, get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time
from auto_complete import character_select, character_select_gm, cc_select, npc_select, condition_select_EPF
import warnings
from sqlalchemy import exc
from utils.Tracker_Getter import get_tracker_model
from utils.utils import gm_check, get_guild
from utils.Util_Getter import get_utilities


warnings.filterwarnings("always", category=exc.RemovedIn20Warning)
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA


#################################################################
#################################################################
# FUNCTIONS

# ---------------------------------------------------------------
# ---------------------------------------------------------------
# SETUP


# Set up the tracker if it does not exist
async def setup_tracker(
    ctx: discord.ApplicationContext,
    engine,
    bot,
    gm: discord.User,
    channel: discord.TextChannel,
    gm_channel: discord.TextChannel,
    system: str,
):
    logging.info("Setup Tracker")

    # Check to make sure bot has permissions in both channels
    if not channel.can_send() or not gm_channel.can_send():
        await ctx.respond(
            "Setup Failed. Ensure VirtualGM has message posting permissions in both channels.", ephemeral=True
        )
        return False

    if system == "Pathfinder 2e":
        g_system = "PF2"
    elif system == "D&D 4e":
        g_system = "D4e"
    elif system == "Enhanced PF2":
        g_system = "EPF"
    else:
        g_system = None

    try:
        metadata = db.MetaData()
        # Build the row in Global first, because the other tables reference it
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            async with session.begin():
                guild = Global(
                    guild_id=ctx.guild.id,
                    time=0,
                    gm=str(gm.id),
                    tracker_channel=channel.id,
                    gm_tracker_channel=gm_channel.id,
                    system=g_system,
                )
                session.add(guild)
            await session.commit()

        # Build the tracker, con and macro tables
        try:
            async with engine.begin() as conn:  # Call the tables directly to save a database call
                await get_tracker_table(ctx, metadata, engine)
                await get_condition_table(ctx, metadata, engine)
                await get_macro_table(ctx, metadata, engine)
                await conn.run_sync(metadata.create_all)

            # Update the pinned trackers
            Tracker_Model = await get_tracker_model(ctx, bot, engine=engine)
            await Tracker_Model.set_pinned_tracker(channel)  # set the tracker in the player channel
            await Tracker_Model.set_pinned_tracker(gm_channel, gm=True)  # set up the gm_track in the GM channel
        except Exception:
            await ctx.respond("Please check permissions and try again")
            await delete_tracker(ctx, engine, bot)
            await engine.dispose()
            return False

        guild = await get_guild(ctx, None, refresh=True)
        if guild.tracker is None or guild.gm_tracker is None:
            await delete_tracker(ctx, engine, bot, guild=guild)
            await ctx.respond("Please check permissions and try again")
            await engine.dispose()
            return False

        await engine.dispose()
        return True

    except Exception as e:
        logging.warning(f"setup_tracker: {e}")
        report = ErrorReport(ctx, setup_tracker.__name__, e, bot)
        await report.report()
        await ctx.respond("Server Setup Failed. Perhaps it has already been set up?", ephemeral=True)
        return False


# Transfer gm permissions
async def set_gm(ctx: discord.ApplicationContext, new_gm: discord.User, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(
                select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id,
                    )
                )
            )
            guild = result.scalars().one()
            guild.gm = str(new_gm.id)  # I accidentally stored the GM as a string instead of an int initially
            # if I ever have to wipe the database, this should be changed
            await session.commit()
        await engine.dispose()

        return True
    except Exception as e:
        logging.warning(f"set_gm: {e}")
        report = ErrorReport(ctx, set_gm.__name__, e, bot)
        await report.report()
        return False


# Delete the tracker
async def delete_tracker(ctx: discord.ApplicationContext, engine, bot, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        # Everything in the opposite order of creation
        metadata = db.MetaData()
        # delete each table
        emp = await get_tracker_table(ctx, metadata, engine, guild=guild)
        con = await get_condition_table(ctx, metadata, engine, guild=guild)
        macro = await get_macro_table(ctx, metadata, engine, guild=guild)

        async with engine.begin() as conn:
            try:
                await conn.execute(DropTable(macro, if_exists=True))
            except Exception:
                logging.warning("Unable to delete Macro Table")
            try:
                await conn.execute(DropTable(con, if_exists=True))
            except Exception:
                logging.warning("Unable to drop Con Table")
            try:
                await conn.execute(DropTable(emp, if_exists=True))
            except Exception:
                logging.warning("Unable to Drop Tracker Table")

        try:
            # delete the row from Global
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            async with async_session() as session:
                result = await session.execute(
                    select(Global).where(
                        or_(
                            Global.tracker_channel == ctx.interaction.channel_id,
                            Global.gm_tracker_channel == ctx.interaction.channel_id,
                        )
                    )
                )
                guild = result.scalars().one()
                await session.delete(guild)
                await session.commit()
        except Exception as e:
            logging.warning(f"guild: delete tracker: {e}")
            report = ErrorReport(ctx, "guild: delete_tracker", e, bot)
            await report.report()
        return True
    except Exception as e:
        logging.warning(f"delete tracker: {e}")
        report = ErrorReport(ctx, "delete_tracker", e, bot)
        await report.report()


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# TRACKER MANAGEMENT





#############################################################################
#############################################################################
# SLASH COMMANDS
# The Initiative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.update_status.start()
        # self.check_latency.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    # @tasks.loop(seconds=30)
    # async def check_latency(self):
    #     logging.info(f"{self.bot.latency}: {datetime.datetime.now()}")

    # Update the bot's status periodically
    @tasks.loop(minutes=1)
    async def update_status(self):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            guild = await session.execute(select(Global))
            result = guild.scalars().all()
            count = len(result)
        async with self.lock:
            await self.bot.change_presence(
                activity=discord.Game(name=f"ttRPGs in {count} tables across the digital universe.")
            )

    # Don't start the loop unti the bot is ready
    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()

    async def time_check_ac(self, ctx: discord.AutocompleteContext):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        if await check_timekeeper(ctx, engine):
            return ["Round", "Minute", "Hour", "Day"]
        else:
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
    @option("hp", description="Total HP", input_type=int)
    @option("player", choices=["player", "npc"], input_type=str)
    @option("initiative", description="Initiative Roll (XdY+Z)", required=True, input_type=str)
    async def add(self, ctx: discord.ApplicationContext, name: str, hp: int, player: str, initiative: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        player_bool = False
        if player == "player":
            player_bool = True
        elif player == "npc":
            player_bool = False

        Utilities = await get_utilities(ctx, engine=engine)
        response = await Utilities.add_character(self.bot, name, hp, player_bool, initiative)
        if response:
            await ctx.respond(f"Character {name} added successfully.", ephemeral=True)
            Tracker_Model = await get_tracker_model(self.ctx, self.bot, guild=self.guild, engine=self.engine)
            await Tracker_Model.update_pinned_tracker()
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
    async def edit(
        self,
        ctx: discord.ApplicationContext,
        name: str,
        hp: int = None,
        initiative: str = None,
        active: bool = None,
        player: discord.User = None,
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        guild = await get_guild(ctx, None)
        response = False
        if await auto_complete.hard_lock(ctx, name):
            Character_Model = await get_character(name, ctx, guild=guild, engine=engine)
            response = await Character_Model.edit_character(name, hp, initiative, active, player, self.bot)
            if not response:
                await ctx.respond("Error Editing Character", ephemeral=True)
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
    async def copy(self, ctx: discord.ApplicationContext, name: str, new_name: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer(ephemeral=True)
        Utilites = await get_utilities(ctx, engine=engine)
        response = False
        response = await Utilites.copy_character(name, new_name)
        if response:
            await ctx.send_followup(f"{new_name} Created", ephemeral=True)
        else:
            await ctx.send_followup("Error Copying Character", ephemeral=True)
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
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
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
                    Utilities = await get_utilities(ctx, guild=guild, engine=engine)
                    result = await Utilities.delete_character(name)
                    if result:
                        await ctx.send_followup(f"{name} deleted", ephemeral=True)
                        Tracker_Model = await get_tracker_model(ctx, self.bot, guild=guild, engine=engine)
                        await Tracker_Model.update_pinned_tracker()
                    else:
                        await ctx.send_followup("Delete Operation Failed", ephemeral=True)
                await engine.dispose()
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
            Character_Model = await get_character(name, ctx, engine=engine)
            embed = await Character_Model.get_char_sheet(self.bot)
            await ctx.send_followup(embeds=embed)
        else:
            ctx.send_followup("You do not have the appropriate permissions to view this character.")

    @i.command(
        description="Manage Initiative",
        # guild_ids=[GUILD]
    )
    @discord.default_permissions(manage_messages=True)
    @option("mode", choices=["start", "stop", "delete character"], required=True)
    @option("character", description="Character to delete", required=False)
    async def manage(self, ctx: discord.ApplicationContext, mode: str, character: str = ""):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
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
                    # print(f"Character {character}")
                    # print(f"Saved: {guild.saved_order}")
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
                        else:
                            await ctx.send_followup("Delete Operation Failed", ephemeral=True)
            await engine.dispose()
        except NoResultFound:
            await ctx.respond(error_not_initialized, ephemeral=True)
            return False
        except IndexError:
            await ctx.respond("Ensure that you have added characters to the initiative list.")
        except Exception:
            await ctx.respond("Failed")

    @i.command(
        description="Advance Initiative",
        # guild_ids=[GUILD]
    )
    async def next(self, ctx: discord.ApplicationContext):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        # try:
        await ctx.response.defer()
        Tracker_Object = await get_tracker_model(ctx, self.bot, engine=engine )
        await Tracker_Object.next()

            # await block_advance_initiative(ctx, engine, self.bot)  # Advance the init
            # await block_post_init(ctx, engine, self.bot)
        # except NoResultFound:
        #     await ctx.respond(error_not_initialized, ephemeral=True)
        # except PermissionError:
        #     await ctx.message.delete()
        # except Exception as e:
        #     await ctx.respond("Error", ephemeral=True)
        #     logging.warning(f"/i next: {e}")
        #     report = ErrorReport(ctx, "slash command /i next", e, self.bot)
        #     await report.report()

    @i.command(
        description="Set Init (Number or XdY+Z)",
        # guild_ids=[GUILD]
    )
    @option(
        "character",
        description="Character to select",
        autocomplete=character_select_gm,
    )
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
                roll = d20.roll(initiative)
                model = await get_character(character, ctx, guild=guild, engine=engine)
                await model.set_init(roll.total)
                await ctx.respond(f"Initiative set to {roll.total} for {character}")
            except Exception as e:
                await ctx.respond(f"Failed to set initiative for {character}.\n{e}", ephemeral=True)
        Tracker_Object = await get_tracker_model(ctx, self.bot, engine=engine)
        await Tracker_Object.update_pinned_tracker()
        await engine.dispose()

    @i.command(
        description="Heal, Damage or add Temp HP",
        # guild_ids=[GUILD]
    )
    @option("name", description="Character Name", autocomplete=character_select)
    @option("mode", choices=["Damage", "Heal", "Temporary HP"])
    async def hp(self, ctx: discord.ApplicationContext, name: str, mode: str, amount: int):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        await ctx.response.defer()
        guild = await get_guild(ctx, None)

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

        if not response:
            await ctx.respond("Failed", ephemeral=True)

        Tracker_Object = await get_tracker_model(ctx, self.bot, engine=engine, guild=guild)
        await Tracker_Object.update_pinned_tracker()
        await engine.dispose()

    @cc.command(
        description="Add conditions and counters",
        # guild_ids=[GUILD]
    )
    @option("character", description="Character to select", autocomplete=character_select)
    @option("title", autocomplete=condition_select_EPF)
    @option("type", choices=["Condition", "Counter"])
    @option("auto", description="Auto Decrement", choices=["Auto Decrement", "Static"])
    @option("unit", autocomplete=time_check_ac)
    @option("flex", autocomplete=discord.utils.basic_autocomplete(["True", "False"]))
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
        data:str = ""
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        if flex == "False":
            flex_bool = False
        else:
            flex_bool = True

        if type == "Condition":
            counter_bool = False
        else:
            counter_bool = True
        if auto == "Auto Decrement":
            auto_bool = True
        else:
            auto_bool = False

        model = await get_character(character, ctx, guild=guild, engine=engine)
        Tracker = await get_tracker_model(ctx, self.bot, guild=guild, engine=engine)
        response = await model.set_cc(title, counter_bool, number, unit, auto_bool, flex=flex_bool, data=data)
        await Tracker.update_pinned_tracker()

        if response:
            await ctx.send_followup(f"Condition {title} added on {character}")
        else:
            await ctx.send_followup("Add Condition/Counter Failed")

    @cc.command(
        description="Edit or remove conditions and counters",
        # guild_ids=[GUILD]
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

        if mode == "delete":
            result = Character_Model.delete_cc(condition)
            if result:
                await ctx.send_followup("Successful Delete", ephemeral=True)
                await ctx.send(f"{condition} on {character} deleted.")
        elif mode == "edit":
            # print("editing")
            if value is not None:
                result = await Character_Model.edit_cc(condition, value)
                if result:
                    await ctx.send_followup(f"{condition} on {character} updated to {value}.")
                else:
                    await ctx.send_followup("Error")
            else:
                output = await ui_components.edit_cc_interface(ctx, engine, character, condition, self.bot)
                if output[0] is not None:
                    await ctx.send_followup(output[0], view=output[1], ephemeral=True)
                else:
                    await ctx.send_followup("Error")
        else:
            await ctx.send_followup("Invalid Input", ephemeral=True)


def setup(bot):
    bot.add_cog(InitiativeCog(bot))
