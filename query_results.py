# query_result.py

# Handles the 4e Query Commands Cog

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

import sqlalchemy as db
from database_models import disease_table, feat_table, power_table
from database_operations import get_db_engine

import os
from dotenv import load_dotenv

from ui_components import QuerySelectButton


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



#############################################################################
#############################################################################
# SLASH COMMANDS
# The Query Cog
class QueryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Set the group's prefix to q
    query = SlashCommandGroup("q", "Fourth Edition Lookup")

    @query.command(description="Power Query")
    async def power(self, ctx: discord.ApplicationContext, query: str):
        # Defer it to allow more than 3 seconds for the query
        await ctx.response.defer()
        # attach to the engine and query the proper table
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        metadata = db.MetaData()
        emp = power_table(metadata)
        stmt = emp.select().where(emp.c.Title.ilike(f'%{query}%'))
        compile = stmt.compile()
        with engine.connect() as conn:
            results = []
            for row in conn.execute(stmt):
                results.append(row)

        # Create the view
        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond("No Results Found")
            return
        # Add a button to the view for each of the first 10 results
        for result in results[0:10]:
            name = f"{result[2]}, Level:{result[3]}"
            link = result[8]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.send_followup(f"Query Results: Powers - {query}", view=view)

    @query.command(description="Power Query")
    async def disease(self, ctx: discord.ApplicationContext, query: str):
        await ctx.response.defer()
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        metadata = db.MetaData()
        emp = disease_table(metadata)
        stmt = emp.select().where(emp.c.Title.ilike(f'%{query}%'))
        compile = stmt.compile()
        print(compile)
        with engine.connect() as conn:
            results = []
            for row in conn.execute(stmt):
                results.append(row)

        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond("No Results Found")
            return
        for result in results[0:10]:
            name = f"{result[2]}, Level: {result[3]}"
            link = result[6]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.send_followup(f"Query Results: Powers - {query}", view=view)

    @query.command(description="Feat Query")
    async def feat(self, ctx: discord.ApplicationContext, query: str):
        await ctx.response.defer()
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        metadata = db.MetaData()
        emp = feat_table(metadata)
        stmt = emp.select().where(emp.c.Title.ilike(f'%{query}%'))
        compile = stmt.compile()
        with engine.connect() as conn:
            results = []
            # print(conn.execute(stmt))
            for row in conn.execute(stmt):
                results.append(row)

        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond("No Results Found")
            return
        for result in results[0:10]:
            name = f"{result[2]}"
            link = result[6]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.send_followup(f"Query Results: Powers - {query}", view=view)


def setup(bot):
    bot.add_cog(QueryCog(bot))
