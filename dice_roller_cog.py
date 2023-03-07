# dice_roller_cog.py
import logging
import os

# imports
import discord
from discord import option
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import d20

# import initiative
from database_models import Global
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.parsing import opposed_roll
from utils.utils import get_guild

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


class DiceRollerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Takes a string and then parses out the string and rolls the dice
    @commands.slash_command(name="r", description="Dice Roller")
    @option("secret", choices=["Secret", "Open"])
    @option("dc", description="Number to which dice result will be compared", required=False)
    async def post(self, ctx: discord.ApplicationContext, roll: str, dc: int = None, secret: str = "Open"):
        try:
            # print('Rolling')
            guild = await get_guild(ctx, None)
            try:
                roll_result = d20.roll(roll)
                roll_str = opposed_roll(roll_result, d20.roll(f"{dc}")) if dc else roll_result
                # print(f"{roll_result =} {roll_str =}")

                if secret == "Secret":
                    if guild.gm_tracker_channel is not None:
                        await ctx.respond("Secret Dice Rolled")
                        await self.bot.get_channel(int(guild.gm_tracker_channel)).send(
                            f"```Secret Roll from {ctx.user.name}```\n{roll}\n{roll_str}"
                        )
                    else:
                        await ctx.respond("No GM Channel Initialized. Secret rolls not possible", ephemeral=True)
                        await ctx.channel.send(f"_{roll}_\n{roll_str}")
                else:
                    await ctx.respond(f"_{roll}_\n{roll_str}")
            except Exception as e:
                logging.warning(f"dice_roller_cog, post: {e}")
                report = ErrorReport(ctx, "dice_roller", e, self.bot)
                await ctx.send_response(f"Failed Rolling: {e}", ephemeral=True)
                await report.report()
        except Exception:  # If the parser doesn't work, assume the format was wrong
            await ctx.send_response(f"Something went wrong with the roll: {roll}.", ephemeral=True)


def setup(bot):
    bot.add_cog(DiceRollerCog(bot))
