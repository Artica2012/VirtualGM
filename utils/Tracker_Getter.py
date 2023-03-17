import logging

import discord

from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Base.Tracker import get_init_list, Tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from EPF.EPF_Tracker import get_EPF_Tracker
from D4e.D4e_Tracker import get_D4e_Tracker
from PF2e.PF2_Tracker import get_PF2_Tracker


async def get_tracker_model(ctx, bot, guild=None, engine=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    init_list = await get_init_list(ctx, engine, guild)
    if guild.system == "EPF":
        return await get_EPF_Tracker(ctx, engine, init_list, bot, guild=guild)
    elif guild.system == "D4e":
        return await get_D4e_Tracker(ctx, engine, init_list, bot, guild=guild)
    elif guild.system == "PF2":
        return await get_PF2_Tracker(ctx, engine, init_list, bot, guild=guild)
    else:
        return Tracker(ctx, engine, init_list, bot, guild=guild)


class NextButton(discord.ui.Button):
    def __init__(self, bot, guild=None):
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        self.guild = guild
        super().__init__(style=discord.ButtonStyle.primary, emoji="➡️")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Initiatve Advanced", ephemeral=True)
            Tracker_Model = await get_tracker_model(None, self.bot, guild=self.guild, engine=self.engine)
            await Tracker_Model.advance_initiative()
            await Tracker_Model.block_post_init()
        except Exception as e:
            print(f"Error: {e}")
            logging.info(e)
