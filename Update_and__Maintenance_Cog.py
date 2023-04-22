# Update_and__Maintenance_Cog.py
import asyncio
import logging
import gc

# imports
import discord
from discord.ext import commands, tasks
from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import D4e.D4e_Tracker
import D4e.d4e_functions
from database_models import Global, Character_Vault, Base, get_tracker
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.Tracker_Getter import get_tracker_model


# ---------------------------------------------------------------
# ---------------------------------------------------------------
class Update_and_Maintenance_Cog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.garbage_collect.start()

    @tasks.loop(minutes=30)
    async def garbage_collect(self):
        collected = gc.collect()
        uncollected = gc.garbage

        logging.warning(f"Garbage Collection.... \nCollected: {collected}  \nUncollected: {len(uncollected)}")

    @commands.Cog.listener()
    async def on_ready(self):
        logging.warning("U&M Cog Loaded")
        # We recreate the view as we did in the /post command.
        view = discord.ui.View(timeout=None)

        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.last_tracker.isnot(None)))
            guild_list = result.scalars().all()

            for guild in guild_list:
                Tracker_Object = await get_tracker_model(None, self.bot, engine=engine, guild=guild)
                Refresh_Button = Tracker_Object.InitRefreshButton(None, self.bot, guild=guild)
                Next_Button = Tracker_Object.NextButton(self.bot, guild=guild)

                try:  # Error handling to avoid locking on a bad message
                    view.clear_items()
                    tracker_channel = self.bot.get_channel(guild.tracker_channel)
                    last_tracker = await tracker_channel.fetch_message(guild.last_tracker)
                    if guild.system == "D4e":
                        view = await D4e.D4e_Tracker.D4eTrackerButtons(None, self.bot, guild)
                    else:
                        view = discord.ui.View(timeout=None)
                    view.add_item(Refresh_Button)
                    view.add_item(Next_Button)
                    await last_tracker.edit(view=view)
                    logging.info(f"{guild.system} - View Updated")
                except Exception as e:
                    logging.error(f"{guild.system} on ready attach buttons: {e} {guild.id}")

        # Character Vault
        # Create Tables that don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.last_tracker.isnot(None)))
            guild_list = result.scalars().all()

            for guild in guild_list:
                Tracker = await get_tracker(None, engine, id=guild.id)
                async with async_session() as tracker_session:
                    result = await tracker_session.execute(select(Tracker).where(Tracker.player == true()))
                    character_list = result.scalars().all()

                for character in character_list:
                    # print(character.name)
                    try:
                        async with async_session() as write_session:
                            query = await write_session.execute(
                                select(Character_Vault)
                                .where(Character_Vault.name == character.name)
                                .where(Character_Vault.guild_id == guild.id)
                            )
                            character_data = query.scalars().one()

                            character_data.guild_id = guild.id
                            character_data.disc_guild_id = guild.guild_id
                            character_data.system = guild.system
                            character_data.name = character.name
                            character_data.user = character.user

                            await write_session.commit()

                    except Exception:
                        async with write_session.begin():
                            new_char = Character_Vault(
                                guild_id=guild.id,
                                system=guild.system,
                                name=character.name,
                                user=character.user,
                                disc_guild_id=guild.guild_id,
                            )
                            write_session.add(new_char)
                        await write_session.commit()

        logging.warning("U&M Complete")
        await engine.dispose()


def setup(bot):
    bot.add_cog(Update_and_Maintenance_Cog(bot))
