import logging

import discord

from Backend.utils.utils import get_guild
from Discord import Bot
from Systems.Base.Tracker import get_init_list, Tracker
from Systems.D4e.D4e_Tracker import get_D4e_Tracker
from Systems.EPF.EPF_Tracker import get_EPF_Tracker
from Systems.PF2e.PF2_Tracker import get_PF2_Tracker
from Systems.RED.RED_Tracker import get_RED_Tracker
from Systems.STF.STF_Tracker import get_STF_Tracker


async def get_tracker_model(ctx, guild=None):
    """
    Function to asychronously query the database and then populate the tracker model intelligently
    with the appropriate model.
    :param ctx:
    :param guild:
    :return: Tracker Model of the appropriate type
    """
    bot = Bot.bot
    guild = await get_guild(ctx, guild)
    init_list = await get_init_list(ctx, guild)
    if guild.system == "EPF":
        return await get_EPF_Tracker(ctx, init_list, bot, guild=guild)
    elif guild.system == "D4e":
        return await get_D4e_Tracker(ctx, bot, guild=guild)
    elif guild.system == "PF2":
        return await get_PF2_Tracker(ctx, init_list, bot, guild=guild)
    elif guild.system == "STF":
        return await get_STF_Tracker(ctx, init_list, bot, guild=guild)
    elif guild.system == "RED":
        return await get_RED_Tracker(ctx, bot, guild=guild)
    else:
        return Tracker(ctx, init_list, bot, guild=guild)


class NextButton(discord.ui.Button):
    def __init__(self, bot, guild=None):
        self.guild = guild
        super().__init__(style=discord.ButtonStyle.primary, emoji="➡️")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("Initiatve Advanced", ephemeral=True)
            Tracker_Model = await get_tracker_model(None, guild=self.guild)
            await Tracker_Model.advance_initiative()
            await Tracker_Model.block_post_init()
        except Exception as e:
            # print(f"Error: {e}")
            logging.info(e)
