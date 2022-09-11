# dice_roller_cog.py

# imports
import discord
from discord.ext import commands
import dice_roller

import os
from dotenv import load_dotenv
import database_operations

# define global variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
DATABASE = os.getenv("DATABASE")


class DiceRollerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Takes a string and then parses out the string and rolls the dice
    @commands.slash_command(name="r", description="Dice Roller")
    async def post(self, ctx: discord.ApplicationContext, roll_string: str):
        try:
            roller = dice_roller.DiceRoller(roll_string)
            await ctx.respond(f"_{roll_string}_\n{roller.roll_dice()}")
        except:
            await ctx.send_response(
                f'Invalid syntax: {roll_string}. \nPlease phrase in ```XdY Label``` format',
                ephemeral=True
            )


def setup(bot):
    bot.add_cog(DiceRollerCog(bot))
