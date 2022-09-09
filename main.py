# main.py

# imports
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

import exporter
import database_operations
import parse

# environmental variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
DATABASE = os.getenv("DATABASE")

# set up the bot/intents
intents = discord.Intents.all()
bot = discord.Bot(intents=intents, debug_guilds=[GUILD])


# Print Status on Connected - Plan to update this to an email or something else once hosted remotely.
@bot.event
async def on_ready():
    print(f"{bot.user} is connected.")

# Initialize the database


parse.parser()
# conn = database_operations.create_connection(DATABASE)

# Load the bot
bot.load_extension("query_results")
bot.load_extension("dice_roller_cog")
bot.load_extension('initiative')
bot.run(TOKEN)
