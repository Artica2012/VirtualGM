# imports
import asyncio
import datetime
import logging

import d20
from sqlalchemy import select, false, true, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_condition, get_tracker, Global
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, get_time, advance_time
from utils.utils import get_guild
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Tracker import Tracker
from utils.Char_Getter import get_character


async def get_D4e_Tracker(ctx, bot, guild=None, engine=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    await get_guild(ctx, guild)
    return D4e_Tracker(ctx, bot, engine=engine, guild=guild)


class D4e_Tracker(Tracker):
    def __init__(self, ctx, bot, engine=None, guild=None):
        super().__init__(ctx, bot, engine, guild)

    async def block_post_init(self):
        logging.info(f"block_post_init")
        # Query the initiative position for the tracker and post it

        try:
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            if self.guild.block:
                turn_list = await self.get_turn_list()
                block = True
                # print(f"block_post_init: \n {turn_list}")
            else:
                block = False
                turn_list = []

            # print(init_list)
            tracker_string = await self.block_get_tracker(guild.initiative)
            # print(tracker_string)
            try:
                logging.info("BPI2")
                ping_string = ""
                if block:
                    for character in turn_list:
                        await asyncio.sleep(0)
                        user = bot.get_user(character.user)
                        ping_string += f"{user.mention}, it's your turn.\n"
                else:
                    user = bot.get_user(init_list[guild.initiative].user)
                    ping_string += f"{user.mention}, it's your turn.\n"
            except Exception:
                # print(f'post_init: {e}')
                ping_string = ""

            # Check for systems:
            if guild.system == "D4e":
                logging.info("BPI3: d4e")
                # view = await D4e.d4e_functions.D4eTrackerButtons(ctx, bot, guild, init_list)
                view = await D4e.d4e_functions.D4eTrackerButtons(ctx, bot, guild=guild)
                # print("Buttons Generated")
                view.add_item(ui_components.InitRefreshButton(ctx, bot, guild=guild))
                view.add_item(ui_components.NextButton(bot, guild=guild))

                if ctx is not None:
                    if ctx.channel.id == guild.tracker_channel:
                        tracker_msg = await ctx.send_followup(f"{tracker_string}\n{ping_string}", view=view)
                    else:
                        await bot.get_channel(guild.tracker_channel).send(
                            f"{tracker_string}\n{ping_string}",
                            view=view,
                        )
                        tracker_msg = await ctx.send_followup("Initiative Advanced.")
                        logging.info("BPI4")
                else:
                    tracker_msg = await bot.get_channel(guild.tracker_channel).send(
                        f"{tracker_string}\n{ping_string}",
                        view=view,
                    )
                    logging.info("BPI4 Guild")
            else:
                view = discord.ui.View(timeout=None)
                view.add_item(ui_components.InitRefreshButton(ctx, bot, guild=guild))
                view.add_item(ui_components.NextButton(bot, guild=guild))
                # Always post the tracker to the player channel
                if ctx is not None:
                    if ctx.channel.id == guild.tracker_channel:
                        tracker_msg = await ctx.send_followup(f"{tracker_string}\n{ping_string}", view=view)
                    else:
                        await bot.get_channel(guild.tracker_channel).send(f"{tracker_string}\n{ping_string}", view=view)
                        tracker_msg = await ctx.send_followup("Initiative Advanced.")
                        logging.info("BPI5")
                else:
                    tracker_msg = await bot.get_channel(guild.tracker_channel).send(
                        f"{tracker_string}\n{ping_string}", view=view
                    )
                    logging.info("BPI5 Guild")
            if guild.tracker is not None:
                channel = bot.get_channel(guild.tracker_channel)
                message = await channel.fetch_message(guild.tracker)
                await message.edit(content=tracker_string)
            if guild.gm_tracker is not None:
                gm_tracker_display_string = await block_get_tracker(
                    init_list, guild.initiative, ctx, engine, bot, gm=True, guild=guild
                )
                gm_channel = bot.get_channel(guild.gm_tracker_channel)
                gm_message = await gm_channel.fetch_message(guild.gm_tracker)
                await gm_message.edit(content=gm_tracker_display_string)

            async with async_session() as session:
                if ctx is None:
                    result = await session.execute(select(Global).where(Global.id == guild.id))
                else:
                    result = await session.execute(
                        select(Global).where(
                            or_(
                                Global.tracker_channel == ctx.interaction.channel_id,
                                Global.gm_tracker_channel == ctx.interaction.channel_id,
                            )
                        )
                    )
                guild = result.scalars().one()
                # print(f"Saved last tracker: {guild.last_tracker}")
                # old_tracker = guild.last_tracker
                try:
                    if guild.last_tracker is not None:
                        tracker_channel = bot.get_channel(guild.tracker_channel)
                        old_tracker_msg = await tracker_channel.fetch_message(guild.last_tracker)
                        await old_tracker_msg.edit(view=None)
                except Exception as e:
                    logging.warning(e)
                guild.last_tracker = tracker_msg.id
                await session.commit()

            await engine.dispose()
        except NoResultFound:
            if ctx is not None:
                await ctx.channel.send(error_not_initialized, delete_after=30)
        except Exception as e:
            logging.error(f"block_post_init: {e}")
            if ctx is not None:
                report = ErrorReport(ctx, block_post_init.__name__, e, bot)
                await report.report()
