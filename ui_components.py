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
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")


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
        await interaction.delete_original_response()
        embed = discord.Embed(title=self.label, timestamp=datetime.datetime.now(), description=self.link)
        await interaction.response.send_message(embed=embed)


class QueryLinkButton(discord.ui.Button):
    def __init__(self, name: str, link: str):
        """A button for one role."""
        super().__init__(label=name, style=discord.ButtonStyle.link, url=link)


class InitRefreshButton(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, bot, guild=None):
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        self.guild = guild
        super().__init__(style=discord.ButtonStyle.primary, emoji="🔁")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Refreshed", ephemeral=True)
            print(interaction.message.id)
            await initiative.update_pinned_tracker(
                self.ctx,
                self.engine,
                self.bot,
                guild=self.guild,
            )
        except Exception as e:
            print(f"Error: {e}")
            logging.info(e)


class NextButton(discord.ui.Button):
    def __init__(self, bot, guild=None):
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        self.guild = guild
        super().__init__(style=discord.ButtonStyle.primary, emoji="➡️")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Initiatve Advanced", ephemeral=True)
            await initiative.block_advance_initiative(None, self.engine, self.bot, guild=self.guild)
            await initiative.block_post_init(None, self.engine, self.bot, guild=self.guild)
        except Exception as e:
            print(f"Error: {e}")
            logging.info(e)


class ConditionAdd(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, bot, character, condition, guild=None):
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        self.character = character
        self.condition = condition
        self.guild = guild
        super().__init__(style=discord.ButtonStyle.primary, emoji="➕")

    async def callback(self, interaction: discord.Interaction):
        try:
            await initiative.increment_cc(self.ctx, self.engine, self.character, self.condition, True, self.bot)
            output = await initiative.edit_cc_interface(self.ctx, self.engine, self.character, self.condition, self.bot)
            print(output[0])
            await interaction.response.edit_message(content=output[0], view=output[1])
            await initiative.update_pinned_tracker(self.ctx, self.engine, self.bot)
        except Exception as e:
            print(f"Error: {e}")
            logging.info(e)


class ConditionMinus(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, bot, character, condition, guild=None):
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        self.character = character
        self.condition = condition
        self.guild = guild
        super().__init__(style=discord.ButtonStyle.primary, emoji="➖")

    async def callback(self, interaction: discord.Interaction):
        try:
            await initiative.increment_cc(self.ctx, self.engine, self.character, self.condition, False, self.bot)
            output = await initiative.edit_cc_interface(self.ctx, self.engine, self.character, self.condition, self.bot)
            print(output[0])
            await interaction.response.edit_message(content=output[0], view=output[1])
            await initiative.update_pinned_tracker(self.ctx, self.engine, self.bot)
        except Exception as e:
            print(f"Error: {e}")
            logging.info(e)
