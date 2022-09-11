import datetime

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

import sqlalchemy as db
from database_models import disease_table, feat_table, power_table
from database_operations import get_db_engine

import os
from dotenv import load_dotenv
import database_operations

# define global variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
DATABASE = os.getenv("DATABASE")
USERNAME = os.getenv('Username')
PASSWORD = os.getenv('Password')
HOSTNAME = os.getenv('Hostname')
PORT = os.getenv('PGPort')


# The Tables:


class QuerySelectButton(discord.ui.Button):
    def __init__(self, name:str, id:str, link:str):
        self.link = link
        super().__init__(
            label=name,
            style=discord.ButtonStyle.primary,
            custom_id=id,
        )

    async def callback(self, interaction: discord.Interaction):
        #Called when button is pressed
        user = interaction.user
        message = interaction.message
        await message.delete()
        embed = discord.Embed(
            title= self.label,
            timestamp=datetime.datetime.now(),
            description=self.link
        )
        await interaction.response.send_message(
            embed=embed
        )


class QueryLinkButton(discord.ui.Button):
    def __init__(self,name: str,  link: str):
        """A button for one role."""
        super().__init__(
            label=name,
            style=discord.ButtonStyle.link,
            url= link
        )


#############################################################################
#############################################################################
# SLASH COMMANDS
# The Query Cog
class QueryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None

    query = SlashCommandGroup("query", "Fourth Edition Lookup")

    @query.command(description="Power Query", guild_ids=[GUILD])
    async def power(self, ctx: discord.ApplicationContext, query: str):
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        metadata = db.MetaData()
        emp = power_table(metadata)
        stmt = emp.select().where(emp.c.Title.ilike(f'%{query}%'))
        compile = stmt.compile()
        with engine.connect() as conn:
            results = []
            for row in conn.execute(stmt):
                results.append(row)

        self.guild = ctx.guild
        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond(("No Results Found"))
            return
        for result in results[0:10]:
            name = f"{result[2]}, Level:{result[3]}"
            link = result[8]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.respond(f"Query Results: Powers - {query}", view=view)

    @query.command(description="Power Query", guild_ids=[GUILD])
    async def disease(self, ctx: discord.ApplicationContext, query: str):
        # conn = database_operations.create_connection(DATABASE)
        # results = database_operations.query_database(conn, "power", query)
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        metadata = db.MetaData()
        emp = disease_table(metadata)
        stmt = emp.select().where(emp.c.Title.ilike(f'%{query}%'))
        compile = stmt.compile()
        print(compile)
        with engine.connect() as conn:
            results = []
            # print(conn.execute(stmt))
            for row in conn.execute(stmt):
                results.append(row)
                # print(row)

        self.guild = ctx.guild
        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond(("No Results Found"))
            return
        for result in results[0:10]:
            name = f"{result[2]}, Level: {result[3]}"
            link = result[6]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.respond(f"Query Results: Powers - {query}", view=view)

    @query.command(description="Feat Query", guild_ids=[GUILD])
    async def feat(self, ctx: discord.ApplicationContext, query: str):
        # conn = database_operations.create_connection(DATABASE)
        # results = database_operations.query_database(conn, "power", query)
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        metadata = db.MetaData()
        emp = feat_table(metadata)
        stmt = emp.select().where(emp.c.Title.ilike(f'%{query}%'))
        # stmt = emp.select()
        compile = stmt.compile()
        # print(compile)
        with engine.connect() as conn:
            results = []
            # print(conn.execute(stmt))
            for row in conn.execute(stmt):
                results.append(row)
                # print(row)

        self.guild = ctx.guild
        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            # print(results)
            await ctx.respond(("No Results Found"))
            return
        for result in results[0:10]:
            name = f"{result[2]}"
            link = result[6]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.respond(f"Query Results: Powers - {query}", view=view)



def setup(bot):
    bot.add_cog(QueryCog(bot))
