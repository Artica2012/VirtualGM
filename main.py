# main.py

# Main file to VirtualGM - a discord bot written with the pycord library

import asyncio
import logging
import os
import sys

import websockets
from dotenv import load_dotenv

import Systems.EPF.Data.Kineticist_DB
import Systems.EPF.Data.Spell_DB
from Backend.API.VGM_API import start_uvicorn
from Backend.WS.WebsocketHandler import socket
from Discord.Bot import bot
from Systems.EPF.EPF_Automation_Data import upload_data


load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    logging.basicConfig(level=logging.WARNING)
    logging.info("Script Started")

else:
    logging.basicConfig(level=logging.INFO)
    logging.info("Script Started")

# logging.basicConfig(level=logging.DEBUG)

TOKEN = os.environ["BOT_TOKEN"]
GUILD = os.getenv("GUILD")
DATABASE = os.getenv("DATABASE")


# Print Status on Connected - Outputs to server log
@bot.event
async def on_ready():
    # logging.warning("Updating tables...")
    #     # database_operations.create_roll_log()
    #
    await upload_data(Systems.EPF.Data.Kineticist_DB.Kineticist_DB)
    await upload_data(Systems.EPF.Data.Spell_DB.Cantrips)
    await upload_data((Systems.EPF.Data.Spell_DB.Psychic_Cantrips))
    logging.warning(f"Connected to {len(bot.guilds)} servers.")
    logging.warning(f"{bot.user} is connected.")
    loop = asyncio.get_running_loop()

    start_uvicorn(loop)
    #
    serve = await websockets.serve(socket.handle, "0.0.0.0", 6270)
    #
    await serve.wait_closed()


@bot.event
async def on_disconnect():
    logging.warning("Disconnected")


@bot.event
async def on_error():
    logging.error(f"on_error: {sys.exc_info()}")


# Load the bot
# bot.load_extension("Query.query_results")
bot.load_extension("Discord.dice_roller_cog")
bot.load_extension("Discord.initiative")
bot.load_extension("Discord.error_reporting_cog")
bot.load_extension("Discord.help_cog")
bot.load_extension("Discord.timekeeping")
bot.load_extension("Discord.macro_cog")
bot.load_extension("Discord.options_cog")
bot.load_extension("Discord.pf2_cog")
bot.load_extension("Discord.automation_cog")
bot.load_extension("Discord.Update_and__Maintenance_Cog")
bot.load_extension("Discord.reminder_cog")
bot.load_extension("Discord.stf_cog")
bot.load_extension("Discord.RED_cog")

bot.run(TOKEN)
