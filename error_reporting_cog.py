# error_reporting_cog.py

import os

# imports
import discord
from discord import option
from discord.ext import commands
from dotenv import load_dotenv

from error_handling_reporting import ErrorReport

# define global variables
load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
else:
    TOKEN = os.getenv("BETA_TOKEN")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")


class ErrorReportingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="bug",
        description="Report a Bug",
        # guild_ids=[GUILD)
    )
    @option("action", description="What were you doing?")
    @option("bug", description="Please describe the bug")
    async def bug(self, ctx: discord.ApplicationContext, action, bug: str):
        try:
            report = ErrorReport(ctx, action, bug, self.bot)
            await report.report()
            await ctx.respond("Bug Reported", ephemeral=True)
        except Exception:
            await ctx.respond("Error", ephemeral=True)


def setup(bot):
    bot.add_cog(ErrorReportingCog(bot))
