# dice_roller_cog.py

import os

# imports
import discord
from discord import option
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

import dice_roller
from database_models import Global
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport

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
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    # Takes a string and then parses out the string and rolls the dice
    @commands.slash_command(name="r", description="Dice Roller")
    @option('secret', choices=['Secret', 'Open'])
    @option('dc', description="Number to which dice result will be compared", required=False)
    async def post(self, ctx: discord.ApplicationContext, roll: str, dc: int = 0, secret: str = 'Open'):
        try:
            roller = dice_roller.DiceRoller(roll)
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            async with async_session() as session:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )
                )
                )
                guild = result.scalar()
            try:
                if secret == 'Secret':
                        if dc == 0:
                            if guild.gm_tracker_channel != None:
                                await ctx.respond(f"Secret Dice Rolled")
                                await self.bot.get_channel(int(guild.gm_tracker_channel)).send(
                                    f"```Secret Roll from {ctx.user.name}```\n{roll}\n{await roller.roll_dice()}")
                            else:
                                await ctx.respond('No GM Channel Initialized. Secret rolls not possible', ephemeral=True)
                                await ctx.channel.send(f"_{roll}_\n{await roller.roll_dice()}")
                        else:
                            if guild.gm_tracker_channel != None:
                                await ctx.respond(f"Secret Dice Rolled")
                                await self.bot.get_channel(int(guild.gm_tracker_channel)).send(
                                    f"```Secret Roll from {ctx.user.name}```\n{roll}\n{await roller.opposed_roll(dc)}")
                            else:
                                await ctx.respond('No GM Channel Initialized. Secret rolls not possible',
                                                  ephemeral=True)
                                await ctx.channel.send(f"_{roll}_\n{await roller.opposed_roll(dc)}")


                else:
                    if dc == 0:
                        await ctx.respond(f"_{roll}_\n{await roller.roll_dice()}")
                    else:
                        await ctx.respond(f"_{roll}_\n{await roller.opposed_roll(dc)}")

                await self.engine.dispose()
            except Exception as e:
                print(f'dice_roller_cog, post: {e}')
                report = ErrorReport(ctx, "dice_roller", e, self.bot)
                await ctx.send_response(
                    f'Invalid syntax: {roll}. \nPlease phrase in ```XdY Label``` format',
                    ephemeral=True
                )
                await report.report()
        except Exception as e:  # If the parser doesn't work, assume the format was wrong
            await ctx.send_response(
                f'Invalid syntax: {roll}. \nPlease phrase in ```XdY Label``` format',
                ephemeral=True
            )


def setup(bot):
    bot.add_cog(DiceRollerCog(bot))
