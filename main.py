# main.py

# imports
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from initialize import connect_test
import database_operations

# environmental variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
DATABASE = os.getenv("DATABASE")

# set up the bot/intents
intents = discord.Intents.all()
bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} is connected.")

connect_test(DATABASE)

conn = database_operations.create_connection(DATABASE)
# bot.load_extension("button_roles")
bot.load_extension("query_results")
bot.load_extension("dice_roller_cog")
bot.run(TOKEN)
