import logging

import discord

import Backend.Database.engine
from Discord import Bot
from Systems.RED.RED_Tracker import get_RED_Tracker
from Backend.Database.database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Systems.Base.Tracker import get_init_list, Tracker
from Backend.Database.database_operations import get_asyncio_db_engine
from Backend.utils.utils import get_guild
from Systems.EPF.EPF_Tracker import get_EPF_Tracker
from Systems.D4e.D4e_Tracker import get_D4e_Tracker
from Systems.PF2e.PF2_Tracker import get_PF2_Tracker
from Systems.STF.STF_Tracker import get_STF_Tracker


async def get_tracker_model(ctx, bot, guild=None, engine=None):
    """
    Function to asychronously query the database and then populate the tracker model intelligently
    with the appropriate model.
    :param ctx:
    :param bot:
    :param guild:
    :param engine:
    :return: Tracker Model of the appropriate type
    """
    if bot is None:
        bot = Bot.bot
    if engine is None:
        engine = Backend.Database.engine.engine
    guild = await get_guild(ctx, guild)
    init_list = await get_init_list(ctx, engine, guild)
    if guild.system == "EPF":
        return await get_EPF_Tracker(ctx, engine, init_list, bot, guild=guild)
    elif guild.system == "D4e":
        return await get_D4e_Tracker(ctx, engine, init_list, bot, guild=guild)
    elif guild.system == "PF2":
        return await get_PF2_Tracker(ctx, engine, init_list, bot, guild=guild)
    elif guild.system == "STF":
        return await get_STF_Tracker(ctx, engine, init_list, bot, guild=guild)
    elif guild.system == "RED":
        return await get_RED_Tracker(ctx, engine, init_list, bot, guild=guild)
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
            # print(f"Error: {e}")
            logging.info(e)
