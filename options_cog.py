# options_cog.py
import inspect
import logging
import os

# imports
from datetime import datetime

import discord
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import Global
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from initiative import setup_tracker, set_gm, delete_tracker
from utils.Tracker_Getter import get_tracker_model
from utils.utils import gm_check
from time_keeping_functions import set_datetime

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


class OptionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def display_options(self, timekeeping: bool, block: bool, system: str):
        embed = discord.Embed(
            title="Optional Modules",
            description=f"Timekeeper: {timekeeping}\nBlock Initiative: {block}\nSystem: {system}",
        )
        return embed

    setup = SlashCommandGroup("admin", "Setup and Admin Functions")

    @setup.command(
        description="Administrative Commands",
        # guild_ids=[GUILD]
    )
    @discord.default_permissions(manage_messages=True)
    @option("gm", description="@Player to transfer GM permissions to.", required=True)
    @option("channel", description="Player Channel", required=True)
    @option("gm_channel", description="GM Channel", required=True)
    @option("system", choices=["Generic", "Pathfinder 2e", "D&D 4e", "Enhanced PF2"], required=False)
    async def start(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
        gm_channel: discord.TextChannel,
        gm: discord.User,
        system: str = "",
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        logging.info(f"{datetime.now()} - {inspect.stack()[0][3]}")
        await ctx.response.defer(ephemeral=True)
        response = await setup_tracker(ctx, engine, self.bot, gm, channel, gm_channel, system)
        if response:
            await ctx.send_followup("Server Setup", ephemeral=True)
            return
        else:
            await ctx.send_followup("Server Setup Failed. Perhaps it has already been set up?", ephemeral=True)

    @setup.command(
        description="Administrative Commands",
        # guild_ids=[GUILD]
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
        logging.info(f"{datetime.now()} - {inspect.stack()[0][3]}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        if not await gm_check(ctx, engine):
            await ctx.respond("GM Restricted Command", ephemeral=True)
            return
        else:
            try:
                if mode == "reset trackers":
                    await ctx.response.defer(ephemeral=True)
                    Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                    response = await Tracker_Model.repost_trackers()
                    if response:
                        await ctx.send_followup("Trackers Placed", ephemeral=True)
                    else:
                        await ctx.send_followup("Error setting trackers")

                elif mode == "transfer gm":
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
                print(f"/admin tracker: {e}")
                report = ErrorReport(ctx, "slash command /admin start", e, self.bot)
                await report.report()

    @setup.command(description="Optional Modules")
    @option(
        "module",
        choices=[
            "View Modules",
            "Timekeeper",
            "Block Initiative",
        ],
    )
    @option("toggle", choices=["On", "Off"], required=False)
    @option("time", description="Number of Seconds per round (optional)", required=False)
    async def options(self, ctx: discord.ApplicationContext, module: str, toggle: str, time: int = 6):
        logging.info(f"{datetime.now()} - {inspect.stack()[0][3]}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        if toggle == "On":
            toggler = True
        else:
            toggler = False
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

                if module == "View Modules":
                    pass
                elif module == "Timekeeper":
                    if toggler and guild.time_year is None:
                        await set_datetime(
                            ctx, engine, self.bot, second=0, minute=0, hour=6, day=1, month=1, year=2001, time=time
                        )
                    else:
                        guild.timekeeping = toggler
                    Tracker_Model = await get_tracker_model(ctx, self.bot, engine=engine)
                    await Tracker_Model.update_pinned_tracker()
                elif module == "Block Initiative":
                    guild.block = toggler
                else:
                    await ctx.send_followup("Invalid Entry", ephemeral=True)
                    return
                await session.commit()

                result = await session.execute(
                    select(Global).where(
                        or_(
                            Global.tracker_channel == ctx.interaction.channel_id,
                            Global.gm_tracker_channel == ctx.interaction.channel_id,
                        )
                    )
                )
                updated_guild = result.scalars().one()
                if updated_guild.system is None:
                    system_str = "Generic"
                elif updated_guild.system == "PF2":
                    system_str = "Pathfinder Second Edition"
                elif updated_guild.system == "D4e":
                    system_str = "D&D 4th Edition"
                else:
                    system_str = "Generic"

                embed = await self.display_options(
                    timekeeping=updated_guild.timekeeping, block=updated_guild.block, system=system_str
                )
                await ctx.send_followup(embed=embed)
            await engine.dispose()
        except NoResultFound:
            await ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            print(f"/admin options: {e}")
            report = ErrorReport(ctx, "/admin options", e, self.bot)
            await report.report()
            return False


def setup(bot):
    bot.add_cog(OptionsCog(bot))
