# imports
import asyncio
import logging

from sqlalchemy import select, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import Global
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from utils.utils import get_guild
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Generic.Tracker import Tracker


async def get_D4e_Tracker(ctx, engine, init_list, bot, guild=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    return D4e_Tracker(ctx, engine, init_list, bot, guild=guild)


class D4e_Tracker(Tracker):
    def __init__(self, ctx, init_list, bot, engine=None, guild=None):
        super().__init__(ctx, init_list, bot, engine, guild)

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

        # Updates the active initiative tracker (not the pinned tracker)
        async def update_pinned_tracker(self):
            logging.info(f"update_pinned_tracker")

            # Query the initiative position for the tracker and post it
            try:
                async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                logging.info(f"BPI1: guild: {self.guild.id}")
                Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
                Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)

                if self.guild.block:
                    # print(guild.id)
                    turn_list = await self.get_turn_list()
                    block = True
                    # print(f"block_post_init: \n {turn_list}")
                else:
                    block = False
                    turn_list = []

                # Fix the Tracker if needed, then refresh the guild
                await self.init_integrity()
                await self.update()

                tracker_string = await self.block_get_tracker(self.guild.initiative)
                try:
                    logging.info("BPI2")
                    ping_string = ""
                    if block:
                        for character in turn_list:
                            await asyncio.sleep(0)
                            user = self.bot.get_user(character.user)
                            ping_string += f"{user.mention}, it's your turn.\n"
                    else:
                        user = self.bot.get_user(self.init_list[self.guild.initiative].user)
                        ping_string += f"{user.mention}, it's your turn.\n"
                except Exception:
                    # print(f'post_init: {e}')
                    ping_string = ""
                view = discord.ui.View(timeout=None)
                # Check for systems:
                if guild.last_tracker is not None:
                    if guild.system == "D4e":
                        logging.info("BPI3: d4e")

                        async with async_session() as session:
                            result = await session.execute(
                                select(Tracker).where(Tracker.name == init_list[guild.initiative].name))
                            char = result.scalars().one()
                        async with async_session() as session:
                            result = await session.execute(
                                select(Condition).where(Condition.character_id == char.id).where(
                                    Condition.flex == true())
                            )
                            conditions = result.scalars().all()
                        for con in conditions:
                            new_button = D4e.d4e_functions.D4eConditionButton(con, ctx, bot, char, guild=guild)
                            view.add_item(new_button)
                        view.add_item(ui_components.InitRefreshButton(ctx, bot, guild=guild))
                        view.add_item((ui_components.NextButton(bot, guild=guild)))
                        tracker_channel = bot.get_channel(guild.tracker_channel)
                        edit_message = await tracker_channel.fetch_message(guild.last_tracker)
                        await edit_message.edit(
                            content=f"{tracker_string}\n{ping_string}",
                            view=view,
                        )

                    else:
                        view.add_item(ui_components.InitRefreshButton(ctx, bot, guild=guild))
                        view.add_item((ui_components.NextButton(bot, guild=guild)))
                        if guild.last_tracker is not None:
                            tracker_channel = bot.get_channel(guild.tracker_channel)
                            edit_message = await tracker_channel.fetch_message(guild.last_tracker)
                            await edit_message.edit(
                                content=f"{tracker_string}\n{ping_string}",
                                view=view,
                            )
                if self.guild.tracker is not None:
                    try:
                        channel = self.bot.get_channel(self.guild.tracker_channel)
                        message = await channel.fetch_message(self.guild.tracker)
                        await message.edit(content=tracker_string)
                    except:
                        logging.warning(f"Invalid Tracker: {self.guild.id}")
                        channel = self.bot.get_channel(self.guild.tracker_channel)
                        await channel.send("Error updating the tracker. Please run `/admin tracker reset trackers`.")

                if self.guild.gm_tracker is not None:
                    try:
                        gm_tracker_display_string = await self.block_get_tracker(self.guild.initiative, gm=True)
                        gm_channel = self.bot.get_channel(self.guild.gm_tracker_channel)
                        gm_message = await gm_channel.fetch_message(self.guild.gm_tracker)
                        await gm_message.edit(content=gm_tracker_display_string)
                    except:
                        logging.warning(f"Invalid GMTracker: {self.guild.id}")
                        channel = self.bot.get_channel(self.guild.gm_tracker_channel)
                        await channel.send("Error updating the gm_tracker. Please run `/admin tracker reset trackers`.")

            except NoResultFound:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
            except Exception as e:
                logging.error(f"block_update_init: {e}")
                report = ErrorReport(self.ctx, "update_pinned_tracker", e, self.bot)
                await report.report()
