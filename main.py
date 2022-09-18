# main.py

import os

# imports
import discord
from dotenv import load_dotenv

import lookup_parser

# environmental variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
DATABASE = os.getenv("DATABASE")

# set up the bot/intents
intents = discord.Intents.all()
bot = discord.Bot(intents=intents,
                  # debug_guilds=[GUILD]
                  )


# Print Status on Connected - Outputs to server log
@bot.event
async def on_ready():
    print(f"{bot.user} is connected.")

# Initialize the database
lookup_parser.parser()

# Load the bot
bot.load_extension("query_results")
bot.load_extension("dice_roller_cog")
bot.load_extension('initiative')
bot.run(TOKEN)
