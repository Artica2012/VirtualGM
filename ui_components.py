# ui_components.py

import datetime
import logging
import os

import discord
from dotenv import load_dotenv

# define global variables
import initiative
from database_operations import get_asyncio_db_engine

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


class QuerySelectButton(discord.ui.Button):
    def __init__(self, name: str, id: str, link: str):
        self.link = link
        super().__init__(
            label=name,
            style=discord.ButtonStyle.primary,
            custom_id=id,
        )

    async def callback(self, interaction: discord.Interaction):
        # Called when button is pressed
        user = interaction.user
        message = interaction.message
        await message.delete()
        embed = discord.Embed(
            title=self.label,
            timestamp=datetime.datetime.now(),
            description=self.link
        )
        await interaction.response.send_message(
            embed=embed
        )


class QueryLinkButton(discord.ui.Button):
    def __init__(self, name: str, link: str):
        """A button for one role."""
        super().__init__(
            label=name,
            style=discord.ButtonStyle.link,
            url=link
        )

class InitRefreshButton(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, bot):
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        super().__init__(
            style=discord.ButtonStyle.primary,
            emoji="🔁"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Refreshed", ephemeral=True)
            await initiative.block_update_init(self.ctx, interaction.message.id, self.engine, self.bot)
        except Exception as e:
            print(f'Error: {e}')
            logging.info(e)
