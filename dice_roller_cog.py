# dice_roller_cog.py

# imports
import discord
from discord import option
from discord.ext import commands
import dice_roller

from database_operations import get_db_engine
from database_models import Global, Base, TrackerTable, ConditionTable
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
import sqlalchemy as db
from error_handling_reporting import ErrorReport

import os
from dotenv import load_dotenv
import database_operations

# define global variables
load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
    USERNAME = os.getenv('Username')
    PASSWORD = os.getenv('Password')
    HOSTNAME = os.getenv('Hostname')
    PORT = os.getenv('PGPort')
else:
    TOKEN = os.getenv('BETA_TOKEN')
    USERNAME = os.getenv('BETA_Username')
    PASSWORD = os.getenv('BETA_Password')
    HOSTNAME = os.getenv('BETA_Hostname')
    PORT = os.getenv('BETA_PGPort')

GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
DATABASE = os.getenv('DATABASE')


class DiceRollerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    # Takes a string and then parses out the string and rolls the dice
    @commands.slash_command(name="r", description="Dice Roller")
    @option('secret', choices=['Secret', 'Open'])
    async def post(self, ctx: discord.ApplicationContext, roll: str, secret:str = 'Open'):
        try:
            roller = dice_roller.DiceRoller(roll)
            try:
                if secret == 'Secret':
                    with Session(self.engine) as session:
                        guild = session.execute(select(Global).filter_by(guild_id=ctx.guild.id)).scalar_one()
                        if guild.gm_tracker_channel != None:
                            await ctx.respond(f"Secret Dice Rolled")
                            await self.bot.get_channel(int(guild.gm_tracker_channel)).send(f"```Secret Roll from {ctx.user.name}\n{roll}\n{roller.roll_dice()}```")
                        else:
                            await ctx.respond('No GM Channel Initialized. Secret rolls not possible',ephemeral=True)
                            await ctx.channel.send(f"_{roll}_\n{roller.roll_dice()}")

                else:
                    await ctx.respond(f"_{roll}_\n{roller.roll_dice()}")
            except Exception as e:
                print(f'dice_roller_cog, post: {e}')
                report = ErrorReport(ctx, "dice_roller", e, self.bot)
                await report.report()
        except Exception as e: # If the parser doesn't work, assume the format was wrong
            await ctx.send_response(
                f'Invalid syntax: {roll}. \nPlease phrase in ```XdY Label``` format',
                ephemeral=True
            )


def setup(bot):
    bot.add_cog(DiceRollerCog(bot))
