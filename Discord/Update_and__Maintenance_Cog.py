# Update_and__Maintenance_Cog.py
import asyncio
import gc
import logging

# imports
import discord
from discord.ext import commands, tasks
from sqlalchemy import select, true

import Systems.D4e.D4e_Tracker
import Systems.D4e.d4e_functions
from Backend.Database.database_models import Global, Character_Vault, Base, get_tracker
from Backend.Database.engine import engine, async_session
from Backend.utils.Char_Getter import get_character
from Backend.utils.Tracker_Getter import get_tracker_model


# ---------------------------------------------------------------
# ---------------------------------------------------------------
class Update_and_Maintenance_Cog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.garbage_collect.start()
        self.update_status.start()
        # self.resource_monitor.start()

    # Update the bot's status periodically
    @tasks.loop(minutes=1)
    async def update_status(self):
        try:
            async with async_session() as session:
                guild = await session.execute(select(Global))
                result = guild.scalars().all()
                count = len(result)
            async with self.lock:
                await self.bot.change_presence(
                    activity=discord.Game(name=f"ttRPGs in {count} tables across the digital universe.")
                )
        except Exception as e:
            logging.error(f"Initiative Cog = Update Status: {e}")

    # Don't start the loop unti the bot is ready
    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=30)
    async def garbage_collect(self):
        collected = gc.collect()

        logging.warning(f"GC: {collected}. Guilds: {len(self.bot.guilds)}")
        logging.warning(await self.get_stats())

    @commands.Cog.listener()
    async def on_ready(self):
        # remove on next load
        # await asyncio.sleep(15)
        logging.warning("U&M Cog Loaded")
        # We recreate the view as we did in the /post command.
        view = discord.ui.View(timeout=None)

        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.last_tracker.isnot(None)))
            guild_list = result.scalars().all()

            for guild in guild_list:
                try:
                    Tracker_Object = await get_tracker_model(None, guild=guild)
                    Refresh_Button = Tracker_Object.InitRefreshButton(None, self.bot, guild=guild)
                    Next_Button = Tracker_Object.NextButton(self.bot, guild=guild)
                except Exception as e:
                    logging.info(f"{guild.system} on ready attach buttons: {e} {guild.id}")

                try:  # Error handling to avoid locking on a bad message
                    view.clear_items()
                    tracker_channel = self.bot.get_channel(guild.tracker_channel)
                    last_tracker = await tracker_channel.fetch_message(guild.last_tracker)
                    if guild.system == "D4e":
                        view = await Systems.D4e.D4e_Tracker.D4eTrackerButtons(None, self.bot, guild)
                    else:
                        view = discord.ui.View(timeout=None)
                    view.add_item(Refresh_Button)
                    view.add_item(Next_Button)
                    await last_tracker.edit(view=view)
                    logging.info(f"{guild.system} - View Updated")
                except Exception as e:
                    logging.info(f"{guild.system} on ready attach buttons: {e} {guild.id}")

        # Character Vault
        # Create Tables that don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.last_tracker.isnot(None)))
            guild_list = result.scalars().all()

            for guild in guild_list:
                Tracker = await get_tracker(None, id=guild.id)
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
                        try:
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
                        except Exception:
                            pass

        await guild_audit_members()

        logging.warning("U&M Complete")

        # Commented out until needed again
        # await self.force_refresh()

        logging.warning(await self.get_stats())

    async def get_stats(self):
        try:
            async with async_session() as session:
                guild = await session.execute(select(Global))
                result = guild.scalars().all()
                total = len(result)

            # counts
            block = 0
            time = 0
            base = 0
            EPF = 0
            PF2 = 0
            STF = 0
            RED = 0
            D4e = 0

            for item in result:
                if item.block:
                    block += 1
                if item.time:
                    time += 1
                if item.system is None:
                    base += 1
                if item.system == "EPF":
                    EPF += 1
                if item.system == "PF2":
                    PF2 += 1
                if item.system == "STF":
                    STF += 1
                if item.system == "RED":
                    RED += 1
                if item.system == "D4e":
                    D4e += 1
            output = (
                f"Total Tables: {total}\n"
                f"Block: {block}, Time: {time} "
                f"Base: {base}, EPF: {EPF}, PF2: {PF2}, STF: {STF}, RED: {RED}, D4e: {D4e}"
            )
            return output
        except Exception:
            return ""

    async def force_refresh(self):
        async with async_session() as session:
            result = await session.execute(select(Global))
            all_guilds = result.scalars().all()

        for guild in all_guilds:
            try:
                Tracker = await get_tracker(None, id=guild.id)
                # Condition = await get_condition(None, engine, id=guild.id)
                async with async_session() as session:
                    result = await session.execute(select(Tracker))
                char_list = result.scalars().all()

                for char in char_list:
                    Character_Model = await get_character(char.name, None, guild=guild)
                    await Character_Model.update()

                    # if guild.system == "EPF":
                    #     con_list = await Character_Model.conditions()
                    #     for item in con_list:
                    #         try:
                    #             if item.number != 0 and item.time is False and item.value is None:
                    #                 async with async_session() as session:
                    #                     result = await session.execute(select(Condition)
                    #                       .where(Condition.id == item.id))
                    #                     mod_con = result.scalars().one()
                    #
                    #                     mod_con.value = mod_con.number
                    #
                    #                     await session.commit()
                    #         except Exception:
                    #             pass
                    # print(Character_Model.char_name, "updated.")

                try:
                    Tracker_Model = await get_tracker_model(None, guild=guild)
                    await Tracker_Model.update_pinned_tracker()
                except Exception:
                    pass
            except Exception as e:
                logging.info(f"{guild.guild_id}: {e}")


def setup(bot):
    bot.add_cog(Update_and_Maintenance_Cog(bot))


async def guild_audit_members():
    async with async_session() as session:
        result = await session.execute(select(Global))
        all_guilds = result.scalars().all()

    for guild in all_guilds:
        try:
            member_list = []
            Tracker = await get_tracker(None, id=guild.id)
            async with async_session() as session:
                result = await session.execute(select(Tracker))
            char_list = result.scalars().all()
            for char in char_list:
                if char.user not in member_list:
                    member_list.append(char.user)

            async with async_session() as session:
                result = await session.execute(select(Global).where(Global.id == guild.id))
                active_guild = result.scalars().one()
                active_guild.members = member_list
                await session.commit()
        except Exception as e:
            logging.warning(f"{guild.id}: {e}")
