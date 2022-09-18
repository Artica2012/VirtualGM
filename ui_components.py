# ui_components.py

import datetime
import discord
import sqlalchemy as db
from database_operations import get_db_engine
from database_models import TrackerTable, ConditionTable, Global
from sqlalchemy import select, update, delete
from initiative import update_pinned_tracker

import os
from dotenv import load_dotenv

# define global variables

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


# Button to delete a condition in the init condition table
class ConditionDeleteButton(discord.ui.Button):
    def __init__(self, id_value: str, interaction: discord.Interaction):
        self.id_value = id_value
        self.interaction = interaction
        super().__init__(
            label='Delete',
            style=discord.ButtonStyle.primary,
            custom_id=id_value
        )

    async def callback(self, interaction: discord.Interaction):
        # Called when button is pressed
        message = interaction.message
        await message.delete()
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        metadata = db.MetaData()
        try:
            con = ConditionTable(self.interaction.guild, metadata).condition_table()
            stmt = delete(con).where(con.c.id == self.id_value)
            compiled = stmt.compile()
            with engine.connect() as conn:
                result = conn.execute(stmt)
        except Exception as e:
            print(e)
            return


class ConditionDropdown(discord.ui.Select):
    def __init__(self, bot_: discord.Bot, options: list):
        self.bot = bot_
        options = options

        super().__init__(
            placeholder="Condition / Counter",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        metadata = db.MetaData()
        view = discord.ui.View()
        # print("Selected")
        # print(self.values)
        select.disable = True
        delete_button = ConditionDeleteButton(self.values[0], interaction)
        view.add_item(item=delete_button)
        await interaction.response.send_message(view=view)
