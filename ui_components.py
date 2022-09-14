import datetime

import discord
import sqlalchemy as db
from database_operations import get_db_engine

import os
from dotenv import load_dotenv

# define global variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
USERNAME = os.getenv('Username')
PASSWORD = os.getenv('Password')
HOSTNAME = os.getenv('Hostname')
PORT = os.getenv('PGPort')



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

# Button to delete a condition in the init condition table
class ConditionDeleteButton(discord.ui.Button):
    def __init__(self, id:int):
        self.id = id
        super().__init__(
            label='Delete',
            style=discord.ButtonStyle.primary,
            custom_id=str(id)
        )

    async def callback(self, interaction: discord.Interaction):
        # Called when button is pressed
        message = interaction.message
        await message.delete()
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        metadata = db.MetaData()

class ConditionDropdown(discord.ui.Select):
    def __init__(self, bot_: discord.Bot, options:list):
        self.bot =bot_
        options = options

        super().__init__(
            placeholder="Condition / Counter",
            min_values=1,
            max_values=1,
            options=options
        )

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message("Changed.", ephemeral=True)