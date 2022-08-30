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

# @bot.slash_command(name="item", guild_ids=[GUILD])
# async def query_menu_item(ctx: discord.ApplicationContext, query: str):
#     conn = database_operations.create_connection(DATABASE)
#     results = database_operations.query_database(conn, "item", query)
#     query_result_string = ""
#     for result in results:
#         line = f"Item: {result[2]}, Link: {result[7]} \n"
#         print(line)
#         query_result_string += line
#         print(query_result_string)
#     await ctx.respond(query_result_string)

# @bot.slash_command(name="power", guild_ids=[GUILD])
# async def query_menu_power(ctx: discord.ApplicationContext, query: str):
#     conn = database_operations.create_connection(DATABASE)
#     results = database_operations.query_database(conn, "power", query)
#     query_result_string = ""
#     for result in results:
#         line = f"Power: {result[2]}, Level: {result[3]}, Action: {result[4]}, Link: {result[7]} \n"
#         query_result_string += line
#     print(query_result_string)
#     await ctx.respond(query_result_string)


connect_test(DATABASE)

conn = database_operations.create_connection(DATABASE)
# bot.load_extension("button_roles")
bot.load_extension("query_results")
bot.run(TOKEN)
