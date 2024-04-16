# options_cog.py
import logging

import discord
import sqlalchemy as db
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands
from sqlalchemy import or_, select
from sqlalchemy.exc import NoResultFound

from Backend.Database.database_models import Global, get_tracker_table, get_condition_table, get_macro_table
from Backend.utils.error_handling_reporting import ErrorReport, error_not_initialized
from Backend.utils.time_keeping_functions import set_datetime
from Backend.utils.Tracker_Getter import get_tracker_model
from Backend.utils.utils import gm_check, get_guild
from Backend.Database.engine import engine, async_session


async def option_autocomplete(ctx: discord.AutocompleteContext):
    try:
        module = ctx.options["module"]
        if module == "Audit Log":
            return ["GM Channel", "DM", "Both", "None"]
        else:
            return ["On", "Off"]
    except Exception:
        return []


class OptionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def display_options(self, timekeeping: bool, block: bool, system: str, audit: str):
        embed = discord.Embed(
            title="Optional Modules",
            description=f"Timekeeper: {timekeeping}\nBlock Initiative: {block}\nSystem: {system}\n Audit Log: {audit}",
        )
        return embed

    setup = SlashCommandGroup("admin", "Setup and Admin Functions")

    @setup.command(
        description="Administrative Commands",
    )
    @discord.default_permissions(manage_messages=True)
    @option("gm", description="@Player to transfer GM permissions to.", required=True)
    @option("channel", description="Player Channel", required=True)
    @option("gm_channel", description="GM Channel", required=True)
    @option(
        "system",
        choices=[
            "Base",
            "Enhanced PF2 (Newest Version with Automation)",
            "(Legacy) Pathfinder 2e (Lacks Automation)",
            "D&D 4e",
            "Cyberpunk RED",
            "Starfinder",
        ],
        required=False,
    )
    async def start(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
        gm_channel: discord.TextChannel,
        gm: discord.User,
        system: str = "",
    ):
        await ctx.response.defer(ephemeral=True)
        try:
            response = await setup_tracker(ctx, engine, self.bot, gm, channel, gm_channel, system)
            if response:
                await ctx.send_followup("Backend Setup", ephemeral=True)
                if system == "Enhanced PF2 (Newest Version with Automation)":
                    doc_msg = await ctx.channel.send(
                        "Enhanced Pathfinder 2e Documentation:\n"
                        " https://docs.google.com/document/d/"
                        "1tD9PNXQ-iOBalvzxpTQ9CvuM2jy6Y_S75Rjjof-WRBk/edit?usp=sharing"
                    )
                    await doc_msg.pin()
                elif system == "(Legacy) Pathfinder 2e (Lacks Automation)":
                    doc_msg = await ctx.channel.send(
                        "Legacy Pathfinder 2e Documentation:\n"
                        "https://docs.google.com/document/d/"
                        "13nJH7xE18fO_SiM-cbCKgq6HbIl3aPIG602rB_nPRik/edit?usp=sharing"
                    )
                    await doc_msg.pin()
                elif system == "Stafinder":
                    doc_msg = await ctx.channel.send(
                        "Starfinder Documentation:\n"
                        "https://docs.google.com/document/d/"
                        "1jCm_b6xE4CsRBOFYaYWU8WB1ake9pjucZMlBspcqhnU/edit?usp=sharing"
                    )
                    await doc_msg.pin()

            else:
                await ctx.send_followup("Backend Setup Failed. Perhaps it has already been set up?", ephemeral=True)
        except Exception as e:
            await ctx.send_followup("Backend Setup Failed", ephemeral=True)
            report = ErrorReport(ctx, "start", e, self.bot)
            await report.report()

    @setup.command(
        description="Administrative Commands",
    )
    @discord.default_permissions(manage_messages=True)
    @option("mode", choices=["transfer gm", "reset trackers", "delete tracker"])
    @option("gm", description="@Player to transfer GM permissions to.", required=False)
    @option("delete", description="Type 'delete' to confirm delete. This cannot be undone.", required=False)
    async def tracker(
        self,
        ctx: discord.ApplicationContext,
        mode: str,
        gm: discord.User = discord.ApplicationContext.user,
        delete: str = "",
    ):
        try:
            if mode == "reset trackers":
                await ctx.response.defer(ephemeral=True)
                Tracker_Model = await get_tracker_model(ctx)
                response = await Tracker_Model.repost_trackers()
                if response:
                    await ctx.send_followup("Trackers Placed", ephemeral=True)
                else:
                    await ctx.send_followup("Error setting trackers")
            else:
                if not await gm_check(ctx) and not ctx.user.guild_permissions.administrator:
                    await ctx.respond("GM Restricted Command", ephemeral=True)
                    return
                else:
                    try:
                        if mode == "transfer gm":
                            if gm is not None:
                                response = await set_gm(ctx, gm, engine, self.bot)
                            else:
                                response = False

                            if response:
                                await ctx.respond(f"GM Permissions transferred to {gm.mention}")
                            else:
                                await ctx.respond("Permission Transfer Failed", ephemeral=True)
                        elif mode == "delete tracker":
                            result = False
                            if delete.lower() == "delete":
                                result = await delete_tracker(ctx, engine, self.bot)
                            if result:
                                await ctx.respond("Successfully Deleted")
                            else:
                                await ctx.respond("Delete Action Failed.")
                        else:
                            await ctx.respond("Failed. Check your syntax and spellings.", ephemeral=True)
                    except NoResultFound:
                        await ctx.respond(error_not_initialized, ephemeral=True)
                    except Exception as e:
                        report = ErrorReport(ctx, "slash command /admin start", e, self.bot)
                        await report.report()
        except NoResultFound as e:
            logging.error(e)
            await ctx.respond(
                "Something went wrong. Make sure VirtualGM all message privileges in the chosen channels and then the"
                " reset trackers option."
            )
            report = ErrorReport(ctx, "slash command /admin start", e, self.bot)
            await report.report()

    @setup.command(description="Optional Modules")
    @option(
        "module",
        choices=["View Modules", "Timekeeper", "Block Initiative", "Audit Log"],
    )
    @option("toggle", autocomplete=option_autocomplete, required=False)
    @option("time", description="Number of Seconds per round (optional)", required=False)
    async def options(self, ctx: discord.ApplicationContext, module: str, toggle: str, time: int = 6):
        await ctx.response.defer()
        if toggle == "On":
            toggler = True
        else:
            toggler = False
        try:
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

                if module == "View Modules":
                    pass
                elif module == "Timekeeper":
                    if toggler and guild.time_year is None:
                        if guild.system == "RED":
                            time = 3
                        await set_datetime(
                            ctx, engine, self.bot, second=0, minute=0, hour=6, day=1, month=1, year=2001, time=time
                        )
                    else:
                        guild.timekeeping = toggler
                    Tracker_Model = await get_tracker_model(ctx)
                    await Tracker_Model.update_pinned_tracker()
                elif module == "Block Initiative":
                    guild.block = toggler
                elif module == "Audit Log":
                    match toggle:  # noqa
                        case "GM Channel":
                            audit = "GM"
                        case "DM":
                            audit = "DM"
                        case "Both":
                            audit = "DM, GM"
                        case "None":
                            audit = ""

                    guild.audit_log = audit

                else:
                    await ctx.send_followup("Invalid Entry", ephemeral=True)
                    return
                await session.commit()

            guild = await get_guild(ctx, guild, refresh=True)
            if guild.system is None:
                system_str = "Base"
            elif guild.system == "PF2":
                system_str = "Pathfinder Second Edition"
            elif guild.system == "D4e":
                system_str = "D&D 4th Edition"
            elif guild.system == "EPF":
                system_str = "Enhanced Pathfinder 2e"
            elif guild.system == "RED":
                system_str = "Cyberpunk RED"
            elif guild.system == "STF":
                system_str = "Starfinder"
            else:
                system_str = "Base"

            embed = await self.display_options(
                timekeeping=guild.timekeeping, block=guild.block, system=system_str, audit=guild.audit_log
            )
            await ctx.send_followup(embed=embed)

        except NoResultFound:
            await ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            # print(f"/admin options: {e}")
            report = ErrorReport(ctx, "/admin options", e, self.bot)
            await report.report()
            return False


def setup(bot):
    bot.add_cog(OptionsCog(bot))


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

    if system == "(Legacy) Pathfinder 2e (Lacks Automation)":
        g_system = "PF2"
    elif system == "D&D 4e":
        g_system = "D4e"
    elif system == "Enhanced PF2 (Newest Version with Automation)":
        g_system = "EPF"
    elif system == "Cyberpunk RED":
        g_system = "RED"
    elif system == "Starfinder":
        g_system = "STF"
    else:
        g_system = None

    try:
        metadata = db.MetaData()
        # Build the row in Global first, because the other tables reference it
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
                await get_tracker_table(ctx, metadata)
                await get_condition_table(ctx, metadata)
                await get_macro_table(ctx, metadata)
                await conn.run_sync(metadata.create_all)

            # Update the pinned trackers
            Tracker_Model = await get_tracker_model(ctx)
            await Tracker_Model.set_pinned_tracker(channel)  # set the tracker in the player channel
            await Tracker_Model.set_pinned_tracker(gm_channel, gm=True)  # set up the gm_track in the GM channel
        except Exception:
            await ctx.respond("Please check permissions and try again")
            await delete_tracker(ctx, engine, bot)
            return False

        guild = await get_guild(ctx, None, refresh=True)
        if guild.tracker is None or guild.gm_tracker is None:
            await delete_tracker(ctx, engine, bot, guild=guild)
            await ctx.respond("Please check permissions and try again")
            return False

        return True

    except Exception as e:
        logging.warning(f"setup_tracker: {e}")
        report = ErrorReport(ctx, setup_tracker.__name__, e, bot)
        await report.report()
        await ctx.respond("Backend Setup Failed. Perhaps it has already been set up?", ephemeral=True)
        return False


async def set_gm(ctx: discord.ApplicationContext, new_gm: discord.User, engine, bot):
    logging.info("set_gm")
    try:
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

        return True
    except Exception as e:
        logging.warning(f"set_gm: {e}")
        report = ErrorReport(ctx, set_gm.__name__, e, bot)
        await report.report()
        return False


async def delete_tracker(ctx: discord.ApplicationContext, engine, bot, guild=None):
    logging.info("delete_tracker")
    try:
        # Everything in the opposite order of creation
        # metadata = db.MetaData()
        # # delete each table
        # emp = await get_tracker_table(ctx, metadata, engine, guild=guild)
        # con = await get_condition_table(ctx, metadata, engine, guild=guild)
        # macro = await get_macro_table(ctx, metadata, engine, guild=guild)

        # async with engine.begin() as conn:
        #     try:
        #         await conn.execute(DropTable(macro, if_exists=True))
        #     except Exception:
        #         logging.warning("Unable to delete Macro Table")
        #     try:
        #         await conn.execute(DropTable(con, if_exists=True))
        #     except Exception:
        #         logging.warning("Unable to drop Con Table")
        #     try:
        #         await conn.execute(DropTable(emp, if_exists=True))
        #     except Exception:
        #         logging.warning("Unable to Drop Tracker Table")

        try:
            # delete the row from Global

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
