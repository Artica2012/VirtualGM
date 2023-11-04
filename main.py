# main.py

# Main file to VirtualGM - a discord bot written with the pycord library

import logging

# imports
import os
import sys

from dotenv import load_dotenv

from Bot import bot

# import tracemalloc

# Set up logging
# warnings.filterwarnings("always", category=exc.RemovedIn20Warning)


# environmental variables - if Production - use the token and database of the production model, if Production is False,
# then its running locally and use the local postgres server and the beta token. This allows one .env and code for both
# testing and production.

# import database_operations


print(os.environ["PRODUCTION"])
load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    # TOKEN = os.getenv("TOKEN")
    logging.basicConfig(level=logging.WARNING)
    logging.info("Script Started")

else:
    # TOKEN = os.getenv("BETA_TOKEN")
    logging.basicConfig(level=logging.INFO)
    logging.info("Script Started")

TOKEN = os.environ["BOT_TOKEN"]
GUILD = os.getenv("GUILD")
DATABASE = os.getenv("DATABASE")

# tracemalloc.start()

# set up the bot/intents
# intents = discord.Intents.default()
# intents.members = True
# # intents.messages = True
# # intents = discord.Intents.all()
# bot = discord.Bot(
#     intents=intents,
#     allowed_mention=discord.AllowedMentions.all()
#     # debug_guilds=[GUILD]
# )


# Print Status on Connected - Outputs to server log
@bot.event
async def on_ready():
    # logging.warning("Updating tables...")
    # await database_operations.update_global_manager()
    # await database_operations.update_tracker_table()
    # await database_operations.update_con_table()
    # database_operations.create_reminder_table()
    # logging.warning("Tables updated")
    logging.warning(f"Connected to {len(bot.guilds)} servers.")
    logging.warning(f"{bot.user} is connected.")


@bot.event
async def on_disconnect():
    # await bot.connect()
    logging.warning("Disconnected")


@bot.event
async def on_error():
    logging.error(f"on_error: {sys.exc_info()}")


# Initialize the database for the 4e lookup
# lookup_parser.parser()

# Load the bot
# bot.load_extension("Query.query_results")
bot.load_extension("dice_roller_cog")
bot.load_extension("initiative")
bot.load_extension("error_reporting_cog")
bot.load_extension("help_cog")
bot.load_extension("timekeeping")
bot.load_extension("macro_cog")
bot.load_extension("options_cog")
bot.load_extension("PF2e.pf2_cog")
bot.load_extension("automation_cog")
bot.load_extension("Update_and__Maintenance_Cog")
bot.load_extension("reminder_cog")
bot.load_extension("STF.stf_cog")
bot.load_extension("RED.RED_cog")

# run the bot
bot.run(TOKEN)
