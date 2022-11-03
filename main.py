# main.py

# imports
import discord
from dotenv import load_dotenv
import os
import lookup_parser
import database_operations


# environmental variables
print(os.environ['PRODUCTION'])
load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
else:
    TOKEN = os.getenv('BETA_TOKEN')
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
    # print("Updating tables...")
    # database_operations.update_con_table()
    # print("Tables updated")
    print(f"{bot.user} is connected.")

@bot.event
async def on_disconnect():
    # await bot.connect()
    print('Disconnected')

# Initialize the database
lookup_parser.parser()

# Load the bot
bot.load_extension("query_results")
bot.load_extension("dice_roller_cog")
bot.load_extension('initiative')
bot.load_extension('error_reporting_cog')
bot.load_extension('help_cog')
bot.load_extension('timekeeping')
bot.load_extension("macro_cog")
bot.load_extension("options_cog")
bot.load_extension("PF2e.pf2_cog")
bot.load_extension("attack_cog")
bot.run(TOKEN)
