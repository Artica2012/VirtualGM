import datetime

import discord
from discord.ext import commands

import os
from dotenv import load_dotenv
import database_operations

# define global variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
DATABASE = os.getenv("DATABASE")

# These are custom from the server. Would probably need to set up the bot to create the roles if
# you were doing this for real

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

class PowerQueryButtonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None

    @commands.slash_command(name="power", guild_ids=[GUILD], description="Power Query")
    async def post(self, ctx: discord.ApplicationContext, query: str):
        conn = database_operations.create_connection(DATABASE)
        results = database_operations.query_database(conn, "power", query)
        self.guild = ctx.guild
        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond(("No Results Found"))
            return
        for result in results:
            name = f"{result[2]}, Level:{result[3]}"
            link = result[8]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.respond(f"Query Results: Powers - {query}", view=view)


class FeatQueryButtonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="feat", guild_ids=[GUILD], description="Feat Query")
    async def post(self, ctx: discord.ApplicationContext, query: str):
        conn = database_operations.create_connection(DATABASE)
        results = database_operations.query_database(conn, "feat", query)
        self.guild = ctx.guild
        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond(("No Results Found"))
            return
        for result in results:
            name = f"{result[2]}"
            link = result[6]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.respond(f"Query Results: Feat - {query}", view=view)


class DiseaseQueryButtonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="disease", guild_ids=[GUILD], description="Disease Query")
    async def post(self, ctx: discord.ApplicationContext, query: str):
        conn = database_operations.create_connection(DATABASE)
        results = database_operations.query_database(conn, "feat", query)
        self.guild = ctx.guild
        view = discord.ui.View(timeout=None)  # Keep it persistent
        if not results:
            await ctx.respond(("No Results Found"))
            return
        for result in results:
            name = f"{result[2]}"
            link = result[6]
            view.add_item((QuerySelectButton(name, f"{name}{ctx.user}", link=link)))
        await ctx.respond(f"Query Results: Disease - {query}", view=view)

def setup(bot):
    bot.add_cog(FeatQueryButtonCog(bot))
    bot.add_cog(PowerQueryButtonCog(bot))
    bot.add_cog(DiseaseQueryButtonCog(bot))