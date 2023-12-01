# imports
import asyncio
import logging
from datetime import datetime

import d20
import discord
from sqlalchemy import select, or_, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Tracker import Tracker
from D4e.d4e_functions import D4e_eval_success, D4e_base_roll
from database_models import Global, get_condition, get_tracker
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, get_time
from utils.Char_Getter import get_character
from utils.utils import get_guild, gm_check


async def get_D4e_Tracker(ctx, engine, init_list, bot, guild=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    init_list = await get_init_list(ctx, engine, guild)
    return D4e_Tracker(ctx, engine, init_list, bot, guild=guild)


async def get_init_list(ctx: discord.ApplicationContext, engine, guild=None):
    logging.info("get_init_list (D4e")
    try:
        if guild is not None:
            try:
                Tracker = await get_tracker(ctx, engine, id=guild.id)
            except Exception:
                Tracker = await get_tracker(ctx, engine)
        else:
            Tracker = await get_tracker(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(
                select(Tracker)
                .where(Tracker.active == true())
                .order_by(Tracker.init.desc())
                .order_by(Tracker.init_string.desc())
                .order_by(Tracker.id)
            )
            init_list = result.scalars().all()
            # for item in init_list:
            #     print(item.name, item.init_string)
            logging.info("GIL: Init list gotten (D4e")
            # print(init_list)
        return init_list

    except Exception:
        logging.error("error in get_init_list")
        return []


class D4e_Tracker(Tracker):
    def __init__(self, ctx, init_list, bot, engine=None, guild=None):
        super().__init__(ctx, init_list, bot, engine, guild)

    async def get_init_list(self, ctx: discord.ApplicationContext, engine, guild=None):
        logging.info("get_init_list (D4e")
        try:
            if guild is not None:
                try:
                    Tracker = await get_tracker(ctx, engine, id=guild.id)
                except Exception:
                    Tracker = await get_tracker(ctx, engine)
            else:
                Tracker = await get_tracker(ctx, engine)
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            async with async_session() as session:
                result = await session.execute(
                    select(Tracker)
                    .where(Tracker.active == true())
                    .order_by(Tracker.init.desc())
                    .order_by(Tracker.init_string.desc())
                    .order_by(Tracker.id)
                )
                init_list = result.scalars().all()
                # for item in init_list:
                #     print(item.name, item.init_string)
                logging.info("GIL: Init list gotten (D4e")
                # print(init_list)
            return init_list

        except Exception:
            logging.error("error in get_init_list")
            return []

    # Updates the active initiative tracker (not the pinned tracker)
    async def update_pinned_tracker(self):
        logging.info("update_pinned_tracker")

        # Query the initiative position for the tracker and post it
        try:
            logging.info(f"BPI1: guild: {self.guild.id}")

            if self.guild.block:
                block = True
                # print(f"block_post_init: \n {turn_list}")
            else:
                block = False

            # Fix the Tracker if needed, then refresh the guild
            await self.init_integrity()
            await self.update()

            tracker_string = await self.block_get_tracker(self.guild.initiative)
            try:
                logging.info("BPI2")
                ping_string = ""
                if block:
                    for player in self.guild.block_data:
                        try:
                            user = self.bot.get_user(player)
                            ping_string += f"{user.mention}, "
                        except Exception:
                            ping_string += "Unknown User, "
                    ping_string += "it's your turn.\n"
                else:
                    user = self.bot.get_user(self.init_list[self.guild.initiative].user)
                    ping_string += f"{user.mention}, it's your turn.\n"
            except Exception:
                # print(f'post_init: {e}')
                ping_string = ""
            view = await D4eTrackerButtons(self.ctx, self.bot, guild=self.guild)
            # Check for systems:
            if self.guild.last_tracker is not None:
                self.Refresh_Button = self.InitRefreshButton(self.ctx, self.bot, guild=self.guild)
                self.Next_Button = self.NextButton(self.bot, guild=self.guild)
                view.add_item(self.Refresh_Button)
                view.add_item(self.Next_Button)
                if self.guild.last_tracker is not None:
                    tracker_channel = self.bot.get_channel(self.guild.tracker_channel)
                    edit_message = await tracker_channel.fetch_message(self.guild.last_tracker)
                    await edit_message.edit(
                        content=f"{tracker_string}\n{ping_string}",
                        view=view,
                    )
            if self.guild.tracker is not None:
                try:
                    channel = self.bot.get_channel(self.guild.tracker_channel)
                    message = await channel.fetch_message(self.guild.tracker)
                    await message.edit(content=tracker_string)
                except Exception:
                    logging.warning(f"Invalid Tracker: {self.guild.id}")
                    channel = self.bot.get_channel(self.guild.tracker_channel)
                    await channel.send("Error updating the tracker. Please run `/admin tracker reset trackers`.")

            if self.guild.gm_tracker is not None:
                try:
                    gm_tracker_display_string = await self.block_get_tracker(self.guild.initiative, gm=True)
                    gm_channel = self.bot.get_channel(self.guild.gm_tracker_channel)
                    gm_message = await gm_channel.fetch_message(self.guild.gm_tracker)
                    await gm_message.edit(content=gm_tracker_display_string)
                except Exception:
                    logging.warning(f"Invalid GMTracker: {self.guild.id}")
                    channel = self.bot.get_channel(self.guild.gm_tracker_channel)
                    await channel.send("Error updating the gm_tracker. Please run `/admin tracker reset trackers`.")

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
        except Exception as e:
            logging.error(f"update_pinned_tracker: {e}")
            report = ErrorReport(self.ctx, "update_pinned_tracker", e, self.bot)
            await report.report()

    async def block_post_init(self):
        logging.info("D4e block_post_init")
        # Query the initiative position for the tracker and post it

        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            if self.guild.block:
                block = True
            else:
                block = False

            # print(init_list)
            tracker_string = await self.block_get_tracker(self.guild.initiative)
            # print(tracker_string)
            try:
                logging.info("BPI2")
                ping_string = ""
                if block:
                    for player in self.guild.block_data:
                        try:
                            user = self.bot.get_user(player)
                            ping_string += f"{user.mention}, "
                        except Exception:
                            ping_string += "Unknown User, "
                    ping_string += "it's your turn.\n"
                else:
                    user = self.bot.get_user(self.init_list[self.guild.initiative].user)
                    ping_string += f"{user.mention}, it's your turn.\n"
            except Exception:
                # print(f'post_init: {e}')
                ping_string = ""

            # Check for systems:

            logging.info("BPI3: d4e!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # view = await D4e.d4e_functions.D4eTrackerButtons(ctx, bot, guild, init_list)
            view = await D4eTrackerButtons(self.ctx, self.bot, guild=self.guild)
            # print("Buttons Generated")
            self.Refresh_Button = self.InitRefreshButton(self.ctx, self.bot, guild=self.guild)
            self.Next_Button = self.NextButton(self.bot, guild=self.guild)
            view.add_item(self.Refresh_Button)
            view.add_item(self.Next_Button)

            if self.ctx is not None:
                if self.ctx.channel.id == self.guild.tracker_channel:
                    tracker_msg = await self.ctx.send_followup(f"{tracker_string}\n{ping_string}", view=view)
                else:
                    await self.bot.get_channel(self.guild.tracker_channel).send(
                        f"{tracker_string}\n{ping_string}",
                        view=view,
                    )
                    tracker_msg = await self.ctx.send_followup("Initiative Advanced.")
                    logging.info("BPI4")
            else:
                tracker_msg = await self.bot.get_channel(self.guild.tracker_channel).send(
                    f"{tracker_string}\n{ping_string}",
                    view=view,
                )
                logging.info("BPI4 Guild")
            if self.guild.tracker is not None:
                channel = self.bot.get_channel(self.guild.tracker_channel)
                message = await channel.fetch_message(self.guild.tracker)
                await message.edit(content=tracker_string)
            if self.guild.gm_tracker is not None:
                gm_tracker_display_string = await self.block_get_tracker(self.guild.initiative, gm=True)
                gm_channel = self.bot.get_channel(self.guild.gm_tracker_channel)
                gm_message = await gm_channel.fetch_message(self.guild.gm_tracker)
                await gm_message.edit(content=gm_tracker_display_string)

            async with async_session() as session:
                if self.ctx is None:
                    result = await session.execute(select(Global).where(Global.id == self.guild.id))
                else:
                    result = await session.execute(
                        select(Global).where(
                            or_(
                                Global.tracker_channel == self.ctx.interaction.channel_id,
                                Global.gm_tracker_channel == self.ctx.interaction.channel_id,
                            )
                        )
                    )
                guild = result.scalars().one()
                # print(f"Saved last tracker: {guild.last_tracker}")
                # old_tracker = guild.last_tracker
                try:
                    if guild.last_tracker is not None:
                        tracker_channel = self.bot.get_channel(guild.tracker_channel)
                        old_tracker_msg = await tracker_channel.fetch_message(guild.last_tracker)
                        await old_tracker_msg.edit(view=None)
                except Exception as e:
                    logging.warning(e)
                guild.last_tracker = tracker_msg.id
                await session.commit()

        except NoResultFound:
            if self.ctx is not None:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
        except Exception as e:
            logging.error(f"block_post_init: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "block_post_init", e, self.bot)
                await report.report()

    async def block_get_tracker(self, selected: int, gm: bool = False):
        # Get the datetime
        # print("Getting D4e Tracker")
        datetime_string = ""
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        if self.guild.block and self.guild.initiative is not None:
            turn_list = await self.get_turn_list()
            block = True
        else:
            block = False
        round = self.guild.round

        # Code for appending the inactive list onto the init_list
        total_list = await self.get_init_list(self.ctx, self.engine, guild=self.guild)
        active_length = len(total_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await self.get_inactive_list()
        if len(inactive_list) > 0:
            total_list.extend(inactive_list)
            # print(f'Total Length: {len(init_list)}')

        try:
            if self.guild.timekeeping:
                datetime_string = (
                    f" {await output_datetime(self.ctx, self.engine, self.bot, guild=self.guild)}"
                    "\n________________________\n"
                )
        except NoResultFound:
            if self.ctx is not None:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
            logging.info("Channel Not Set Up")
        except Exception as e:
            logging.error(f"get_tracker: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "get_tracker", e, self.bot)
                await report.report()

        try:
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)

            if round != 0:
                round_string = f"Round: {round}"
            else:
                round_string = ""

            output_string = f"```{datetime_string}Initiative: {round_string}\n"

            for x, row in enumerate(total_list):
                character = await get_character(row.name, self.ctx, engine=self.engine, guild=self.guild)
                logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
                if len(total_list) > active_length and x == active_length:
                    output_string += "-----------------\n"  # Put in the divider
                # print(f'row.id= {row.id}')
                async with async_session() as session:
                    result = await session.execute(
                        select(Condition).where(Condition.character_id == row.id).where(Condition.visible == true())
                    )
                    condition_list = result.scalars().all()

                await asyncio.sleep(0)
                sel_bool = False
                selector = "  "

                # don't show an init if not in combat
                if character.init == 0 or character.active is False:
                    init_num = ""
                else:
                    if character.init <= 9:
                        init_num = f" {row.init}"
                    else:
                        init_num = f"{row.init}"

                if block:
                    for char in turn_list:
                        if character.id == char.id:
                            sel_bool = True
                else:
                    if x == selected:
                        sel_bool = True

                # print(f"{row['name']}: x: {x}, selected: {selected}")

                if sel_bool:
                    selector = ">>"
                if row.player or gm:
                    if row.temp_hp != 0:
                        string = (
                            f"{selector}  {init_num} {str(character.char_name).title()}:"
                            f" {character.current_hp}/{character.max_hp} ({character.temp_hp} Temp)\n"
                        )
                    else:
                        string = (
                            f"{selector}  {init_num} {str(character.char_name).title()}:"
                            f" {character.current_hp}/{character.max_hp}\n"
                        )
                else:
                    string = f"{selector}  {init_num} {str(row.name).title()}: {await character.calculate_hp()} \n"
                output_string += string

                for con_row in condition_list:
                    await asyncio.sleep(0)
                    if con_row.visible is True:
                        if gm or not con_row.counter:
                            if con_row.number is not None and con_row.number > 0:
                                if con_row.time:
                                    time_stamp = datetime.fromtimestamp(con_row.number)
                                    current_time = await get_time(self.ctx, self.engine, guild=self.guild)
                                    time_left = time_stamp - current_time
                                    days_left = time_left.days
                                    processed_minutes_left = divmod(time_left.seconds, 60)[0]
                                    processed_hours_left = divmod(processed_minutes_left, 60)[0]
                                    processed_minutes_left = divmod(processed_minutes_left, 60)[1]
                                    processed_seconds_left = divmod(time_left.seconds, 60)[1]
                                    if processed_seconds_left < 10:
                                        processed_seconds_left = f"0{processed_seconds_left}"
                                    if processed_minutes_left < 10:
                                        processed_minutes_left = f"0{processed_minutes_left}"
                                    if days_left != 0:
                                        con_string = (
                                            f"       {con_row.title}: {days_left} Days,"
                                            f" {processed_minutes_left}:{processed_seconds_left}\n"
                                        )
                                    else:
                                        if processed_hours_left != 0:
                                            con_string = (
                                                f"       {con_row.title}:"
                                                f" {processed_hours_left}:{processed_minutes_left}:"
                                                f"{processed_seconds_left}\n"
                                            )
                                        else:
                                            con_string = (
                                                f"       {con_row.title}:"
                                                f" {processed_minutes_left}:{processed_seconds_left}\n"
                                            )
                                else:
                                    con_string = f"       {con_row.title}: {con_row.number}\n"
                            else:
                                con_string = f"       {con_row.title}\n"

                        elif con_row.counter is True and sel_bool and row.player:
                            con_string = f"       {con_row.title}: {con_row.number}\n"
                        else:
                            con_string = ""
                        output_string += con_string
                    else:
                        con_string = ""
                        output_string += con_string
            output_string += "```"
            # print(output_string)
            await self.update()
            return output_string
        except Exception as e:
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "block_get_tracker (d4e)", e, self.bot)
                await report.report()
            logging.info(f"d4e_get_tracker: {e}")

    class InitRefreshButton(discord.ui.Button):
        def __init__(self, ctx: discord.ApplicationContext, bot, guild=None):
            self.ctx = ctx
            self.engine = get_asyncio_db_engine(
                user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA
            )
            self.bot = bot
            self.guild = guild
            super().__init__(style=discord.ButtonStyle.primary, emoji="🔁")

        async def callback(self, interaction: discord.Interaction):
            try:
                await interaction.response.send_message("Refreshed", ephemeral=True)
                # print(interaction.message.id)
                Tracker_model = D4e_Tracker(
                    self.ctx,
                    self.engine,
                    await get_init_list(self.ctx, self.engine, self.guild),
                    self.bot,
                    guild=self.guild,
                )
                await Tracker_model.update_pinned_tracker()
            except Exception as e:
                # print(f"Error: {e}")
                logging.info(e)
            # await self.engine.dispose()

    class NextButton(discord.ui.Button):
        def __init__(self, bot, guild=None):
            self.engine = get_asyncio_db_engine(
                user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA
            )
            self.bot = bot
            self.guild = guild
            super().__init__(
                style=discord.ButtonStyle.primary, emoji="➡️" if not guild.block or len(guild.block_data) < 2 else "✔"
            )

        async def callback(self, interaction: discord.Interaction):
            try:
                Tracker_Model = D4e_Tracker(
                    None,
                    self.engine,
                    await get_init_list(None, self.engine, self.guild),
                    self.bot,
                    guild=self.guild,
                )
                await Tracker_Model.block_next(interaction)
            except Exception as e:
                # print(f"Error: {e}")
                logging.info(e)


async def D4eTrackerButtons(ctx: discord.ApplicationContext, bot, guild=None):
    # print("D4e Tracker Buttons")
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    # print(guild.id)
    # print(guild.initiative)
    guild = await get_guild(ctx, guild, refresh=True)
    tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    view = discord.ui.View(timeout=None)

    if guild.initiative is None:
        return view

    init_list = await get_init_list(ctx, engine, guild=guild)

    async with async_session() as session:
        result = await session.execute(select(tracker).where(tracker.name == init_list[guild.initiative].name))
        char = result.scalars().one()

    async with async_session() as session:
        result = await session.execute(
            select(Condition).where(Condition.character_id == char.id).where(Condition.flex == true())
        )
        conditions = result.scalars().all()
        # print(len(conditions))
    for con in conditions:
        new_button = D4eConditionButton(con, ctx, bot, char, guild=guild)
        view.add_item(new_button)
    return view


class D4eConditionButton(discord.ui.Button):
    def __init__(self, condition, ctx: discord.ApplicationContext, bot, character, guild=None):
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

        self.bot = bot
        self.character = character
        self.condition = condition
        self.guild = guild
        super().__init__(
            label=condition.title,
            style=discord.ButtonStyle.primary,
            custom_id=str(f"{condition.character_id}_{condition.title}"),
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Saving...")
        Tracker_Model = await get_D4e_Tracker(
            self.ctx,
            self.engine,
            await get_init_list(self.ctx, self.engine, guild=self.guild),
            self.bot,
            guild=self.guild,
        )
        if interaction.user.id == self.character.user or gm_check(self.ctx, self.engine):
            try:
                try:
                    Character_Model = await get_character(
                        self.character.name, self.ctx, engine=self.engine, guild=self.guild
                    )
                    roll_string = "1d20"
                    dice_result = d20.roll(roll_string)
                    success_string = D4e_eval_success(dice_result, D4e_base_roll)
                    # Format output string
                    output_string = f"Save: {self.character.name}\n{dice_result}\n{success_string}"
                    # CC modify
                    if dice_result.total >= D4e_base_roll.total:
                        await Character_Model.delete_cc(self.condition.title)
                except NoResultFound:
                    if self.ctx is not None:
                        await self.ctx.channel.send(error_not_initialized, delete_after=30)
                    return "Error"
                except Exception as e:
                    logging.warning(f"save: {e}")
                    return "Error"
                await interaction.edit_original_response(content=output_string)
                await Tracker_Model.update_pinned_tracker()
            except Exception:
                output_string = "Unable to process save, perhaps the condition was removed."
                await interaction.edit_original_response(content=output_string)
        else:
            output_string = "Roll your own save!"
            await interaction.edit_original_response(content=output_string)

        # await self.engine.dispose()

        # await self.ctx.channel.send(output_string)
