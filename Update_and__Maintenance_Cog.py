# Update_and__Maintenance_Cog.py
# For slash commands specific to oathfinder 2e
# system specific module
import logging

# imports
import discord
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import Base.Tracker
import D4e.D4e_Tracker
import D4e.d4e_functions
from database_models import Global
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.Auto_Complete_Getter import get_autocomplete
from utils.Tracker_Getter import NextButton


# ---------------------------------------------------------------
# ---------------------------------------------------------------
class Update_and_Maintenance_Cog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("U&M Cog Loaded")
        # We recreate the view as we did in the /post command.
        view = discord.ui.View(timeout=None)

        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.last_tracker.isnot(None)))
            guild_list = result.scalars().all()

            for guild in guild_list:
                if guild.system == "D4e":
                    try:# Error handling to avoid locking on a bad message
                        view.clear_items()
                        tracker_channel = self.bot.get_channel(guild.tracker_channel)
                        last_tracker = await tracker_channel.fetch_message(guild.last_tracker)

                        view = await D4e.D4e_Tracker.D4eTrackerButtons(None, self.bot, guild)
                        view.add_item(Base.Tracker.InitRefreshButton(None, self.bot, guild=guild))
                        view.add_item(NextButton(self.bot, guild=guild))
                        await last_tracker.edit(view=view)
                        logging.info("D4e View Updated")
                    except Exception as e:
                        logging.error(f"d4e on ready attach buttons: {e} {guild.id}")
                        # TODO add in more robust error reporting for this to see if it becomes an issue

                else:
                    try:
                        view.clear_items()
                        tracker_channel = self.bot.get_channel(guild.tracker_channel)
                        last_tracker = await tracker_channel.fetch_message(guild.last_tracker)
                        view = discord.ui.View(timeout=None)
                        view.add_item(Base.Tracker.InitRefreshButton(None, self.bot, guild=guild))
                        view.add_item(Base.Tracker.NextButton(self.bot, guild=guild))
                        await last_tracker.edit(view=view)
                        logging.info("View Updated")
                    except Exception as e:
                        logging.error(f"pf2 on ready attach buttons: {e} {guild.id}")
                        # TODO add in more robust error reporting for this to see if it becomes an issue


def setup(bot):
    bot.add_cog(Update_and_Maintenance_Cog(bot))
