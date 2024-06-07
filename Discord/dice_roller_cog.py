# dice_roller_cog.py
import logging

import d20

# imports
import discord
from discord import option
from discord.ext import commands

from Backend.Database.database_operations import log_roll

# import initiative
from Backend.utils.error_handling_reporting import ErrorReport
from Backend.utils.parsing import opposed_roll
from Backend.utils.utils import get_guild, relabel_roll


class DiceRollerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Takes a string and then parses out the string and rolls the dice
    @commands.slash_command(name="r", description="Dice Roller")
    @option("secret", choices=["Secret", "Open"])
    @option("dc", description="Number to which dice result will be compared", required=False)
    async def post(self, ctx: discord.ApplicationContext, roll: str, dc: int = None, secret: str = "Open"):
        roll = relabel_roll(roll)
        guild = await get_guild(ctx, None)
        try:
            try:
                roll_result = d20.roll(roll)
                roll_str = opposed_roll(roll_result, d20.roll(f"{dc}")) if dc else roll_result

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

                # print("Logging")
                if secret == "Secret":
                    secBool = True
                else:
                    secBool = False
                if int(ctx.channel.id) == int(guild.gm_tracker_channel):
                    secBool = True

                user = ctx.user.name
                log_output = f"{roll}:\n{roll_result}"
                await log_roll(guild.id, user, log_output, secret=secBool)

            except Exception as e:
                logging.warning(f"dice_roller_cog, post: {e}")
                report = ErrorReport(ctx, "dice_roller", e, self.bot)
                await ctx.send_response(f"Failed Rolling: {e}", ephemeral=True)
                await report.report()
        except Exception:  # If the parser doesn't work, assume the format was wrong
            await ctx.send_response(f"Something went wrong with the roll: {roll}.", ephemeral=True)


def setup(bot):
    bot.add_cog(DiceRollerCog(bot))
