# query_result.py

# Handles the 4e Query Commands Cog
import asyncio
import os

import discord
import sqlalchemy as db
from discord import option
from discord.ext import commands
from dotenv import load_dotenv

from database_models import disease_table, feat_table, power_table, monster_table, ritual_table
from database_operations import get_asyncio_db_engine
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
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)

    # Set the group's prefix to q

    @commands.slash_command(name="q", description='D&D Fourth Edition Lookup')
    @option('category', choices=[
        'Power', 'Disease', 'Feat', 'Monster', 'Ritual'
    ])
    async def q(self, ctx: discord.ApplicationContext, category: str, query: str):
        await ctx.response.defer()
        metadata = db.MetaData()
        # try:
        if category == "Power":
            emp = power_table(metadata)
        elif category == "Disease":
            emp = disease_table(metadata)
        elif category == "Feat":
            emp = feat_table(metadata)
        elif category == "Monster":
            emp = monster_table(metadata)
        elif category == "Ritual":
            emp = ritual_table(metadata)
        else:
            ctx.send_followup("Error, Invalid")
            return
        stmt = emp.select().where(emp.c.Title.ilike(f'%{query}%'))

        async with self.engine.begin() as conn:
            results = []
            for row in await conn.execute(stmt):
                await asyncio.sleep(0)
                results.append(row)

        # Create the view
        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond("No Results Found")
            return
        # Add a button to the view for each of the first 10 results
        for result in results[0:10]:
            await asyncio.sleep(0)
            name = f"{result[2]}"
            link = result[3]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.send_followup(f"Query Results: {category} - {query}", view=view)
        # except Exception as e:
        #     report = ErrorReport(ctx, "query", e, self.bot)
        #     await report.report()

    # @query.command(description="Monster Query")
    # async def item(self, ctx: discord.ApplicationContext, query: str):
    #     await ctx.response.defer()
    #     engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    #     metadata = db.MetaData()
    #     try:
    #         emp = item_table(metadata)
    #         stmt = emp.select().where(emp.c.Title.ilike(f'%{query}%'))
    #         compiled = stmt.compile()
    #         # print(compiled)
    #         with engine.connect() as conn:
    #             results = []
    #             for row in conn.execute(stmt):
    #                 results.append(row)
    #
    #         view = discord.ui.View(timeout=None)  # Keep it persistent
    #         if not results:
    #             await ctx.respond("No Results Found")
    #             return
    #         for result in results[0:10]:
    #             name = f"{result[2]}"
    #             link = result[4]
    #             view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
    #         await ctx.send_followup(f"Query Results: Powers - {query}", view=view)
    #     except Exception as e:
    #         report = ErrorReport(ctx, "monster query", e, self.bot)
    #         await report.report()


def setup(bot):
    bot.add_cog(QueryCog(bot))
