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

    @commands.slash_command(guild_ids=[GUILD], name="r", description="Dice Roller")
    async def post(self, ctx: discord.ApplicationContext, roll_string: str):
        roller = dice_roller.DiceRoller(roll_string)
        await ctx.respond(f"_{roll_string}_\n{roller.roll_dice()}")


def setup(bot):
    bot.add_cog(DiceRollerCog(bot))
