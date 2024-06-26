# timekeeping.py

from typing import Optional

import discord
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands
from sqlalchemy.exc import NoResultFound

from Backend.utils.Tracker_Getter import get_tracker_model
from Backend.utils.error_handling_reporting import ErrorReport
from Backend.utils.time_keeping_functions import output_datetime, set_datetime, advance_time


# Timekeeper Cog - For managing the time functions
class TimekeeperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    timekeeper = SlashCommandGroup("time", "Time Keeper")

    @timekeeper.command(description="Set Date/Time")
    async def set(
        self,
        ctx: discord.ApplicationContext,
        minute: Optional[int] = None,
        hour: Optional[int] = None,
        day: Optional[int] = None,
        month: Optional[int] = None,
    ):
        try:
            result = await set_datetime(
                ctx, self.bot, second=0, minute=minute, hour=hour, day=day, month=month, year=None
            )
            if result:
                await ctx.respond("Date and Time Set", ephemeral=True)
                Tracker_Model = await get_tracker_model(ctx)
                await Tracker_Model.check_cc()
                await Tracker_Model.update_pinned_tracker()
            else:
                await ctx.respond("Error Setting Date and Time", ephemeral=True)
        except NoResultFound:
            await ctx.respond(
                (
                    "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
                    "proper channel or run `/i admin setup` to setup the initiative tracker"
                ),
                ephemeral=True,
            )
        except Exception as e:
            report = ErrorReport(ctx, "/set_time", e, self.bot)
            await report.report()
            await ctx.respond("Setup Failed")

    @timekeeper.command(description="Advance Time")
    @option("amount", description="Amount to advance")
    @option("unit", choices=["minute", "hour", "day"])
    async def advance(self, ctx: discord.ApplicationContext, amount: int, unit: str = "minute"):
        try:
            if unit == "minute":
                result = await advance_time(ctx, minute=amount)
            elif unit == "hour":
                result = await advance_time(ctx, hour=amount)
            elif unit == "day":
                result = await advance_time(ctx, day=amount)
            else:
                result = False

            if result:
                await ctx.respond(
                    f"Time advanced by {amount} {unit}(s). New time is: {await output_datetime(ctx, self.bot)}"
                )
                Tracker_Model = await get_tracker_model(ctx)
                await Tracker_Model.check_cc()
                await Tracker_Model.update_pinned_tracker()
            else:
                await ctx.respond("Failed to advance time.")
        except Exception:
            await ctx.respond("Error", ephemeral=True)


def setup(bot):
    bot.add_cog(TimekeeperCog(bot))
