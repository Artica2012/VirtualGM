# dice_roller_cog.py

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
from database_models import Global
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport

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
            roller = d20.Roller()
            engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
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
                guild = result.scalar()
            try:
                roll_dc: str = f"{roll} >= {dc}"
                if secret == "Secret":
                    if not dc:
                        if guild.gm_tracker_channel is not None:
                            await ctx.respond("Secret Dice Rolled")
                            await self.bot.get_channel(int(guild.gm_tracker_channel)).send(
                                f"```Secret Roll from {ctx.user.name}```\n{roll}\n{await roller.roll(roll)}"
                            )
                        else:
                            await ctx.respond("No GM Channel Initialized. Secret rolls not possible", ephemeral=True)
                            await ctx.channel.send(f"_{roll}_\n{await roller.roll(roll)}")
                    else:
                        if guild.gm_tracker_channel is not None:
                            await ctx.respond("Secret Dice Rolled")
                            await self.bot.get_channel(int(guild.gm_tracker_channel)).send(
                                f"```Secret Roll from {ctx.user.name}```\n{roll}\n{await roller.roll(roll_dc)}"
                            )
                        else:
                            await ctx.respond("No GM Channel Initialized. Secret rolls not possible", ephemeral=True)
                            await ctx.channel.send(f"_{roll}_\n{await roller.roll(roll_dc)}")

                else:
                    if not dc:
                        await ctx.respond(f"_{roll}_\n{await roller.roll_dice(roll)}")
                    else:
                        await ctx.respond(f"_{roll}_\n{await roller.opposed_roll(roll_dc)}")

                await engine.dispose()
            except Exception as e:
                print(f"dice_roller_cog, post: {e}")
                report = ErrorReport(ctx, "dice_roller", e, self.bot)
                await ctx.send_response(
                    f"Invalid syntax: {roll}. \nPlease phrase in ```XdY Label``` format", ephemeral=True
                )
                await report.report()
        except Exception:  # If the parser doesn't work, assume the format was wrong
            await ctx.send_response(
                f"Invalid syntax: {roll}. \nPlease phrase in ```XdY Label``` format", ephemeral=True
            )


def setup(bot):
    bot.add_cog(DiceRollerCog(bot))
