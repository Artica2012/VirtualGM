# imports
import asyncio
import logging
from datetime import datetime

import discord
from sqlalchemy import select, or_, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import ui_components
from D4e import d4e_functions
from D4e.d4e_functions import gm_check, save
from database_models import Global, get_condition, get_tracker
from database_operations import get_asyncio_db_engine, USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, get_time
from utils.Char_Getter import get_character
# from utils.Tracker_Getter import get_tracker_model
from utils.utils import get_guild
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Generic.Tracker import Tracker, get_init_list


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

        # try:
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        if self.guild.block:
            turn_list = await self.get_turn_list()
            block = True
            # print(f"block_post_init: \n {turn_list}")
        else:
            block = False
            turn_list = []

        # print(init_list)
        tracker_string = await self.block_get_tracker(self.guild.initiative)
        # print(tracker_string)
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

        # Check for systems:

        logging.info("BPI3: d4e")
        # view = await D4e.d4e_functions.D4eTrackerButtons(ctx, bot, guild, init_list)
        view = await D4eTrackerButtons(self.ctx, self.bot, guild=self.guild)
        # print("Buttons Generated")
        view.add_item(ui_components.InitRefreshButton(self.ctx, self.bot, guild=self.guild))
        view.add_item(ui_components.NextButton(self.bot, guild=self.guild))

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

        # except NoResultFound:
        #     if self.ctx is not None:
        #         await self.ctx.channel.send(error_not_initialized, delete_after=30)
        # except Exception as e:
        #     logging.error(f"block_post_init: {e}")
        #     if self.ctx is not None and self.bot is not None:
        #         report = ErrorReport(self.ctx, "block_post_init", e, self.bot)
        #         await report.report()

    async def block_get_tracker(self, selected: int, gm: bool = False):
        # Get the datetime
        datetime_string = ""
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)


        if self.guild.block and self.guild.initiative is not None:
            turn_list = await self.get_turn_list()
            block = True
        else:
            block = False
        round = self.guild.round

        # Code for appending the inactive list onto the init_list
        total_list = self.init_list
        active_length = len(total_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await self.get_inactive_list()
        if len(inactive_list) > 0:
            total_list.extend(inactive_list)
            # print(f'Total Length: {len(init_list)}')

        try:
            if self.guild.timekeeping:
                datetime_string = f" {await output_datetime(self.ctx, self.engine, self.bot, guild=self.guild)}\n________________________\n"
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
                selector = ""

                # don't show an init if not in combat
                if character.init == 0 or character.active is False:
                    init_num = ""
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
                            f" {character.current_hp}/{character.max_hp} ({character.temp_hp}) Temp\n"
                        )
                    else:
                        string = f"{selector}  {init_num} {str(character.char_name).title()}: {character.current_hp}/{character.max_hp}\n"
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
                                                f"       {con_row.title}: {processed_hours_left}:{processed_minutes_left}:{processed_seconds_left}\n"
                                            )
                                        else:
                                            con_string = (
                                                f"       {con_row.title}: {processed_minutes_left}:{processed_seconds_left}\n"
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


async def D4eTrackerButtons(ctx: discord.ApplicationContext, bot, guild=None):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    guild = await get_guild(ctx, guild, refresh=True)
    Tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    view = discord.ui.View(timeout=None)


    init_list = await get_init_list(ctx, engine, guild=guild)

    async with async_session() as session:
        result = await session.execute(select(Tracker).where(Tracker.name == init_list[guild.initiative].name))
        char = result.scalars().one()

    async with async_session() as session:
        result = await session.execute(
            select(Condition).where(Condition.character_id == char.id).where(Condition.flex == true())
        )
        conditions = result.scalars().all()
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
        Tracker_Model = await get_D4e_Tracker(self.ctx, self.engine, await get_init_list(self.ctx, self.engine, guild=self.guild), self.bot, guild=self.guild)
        if interaction.user.id == self.character.user or gm_check(self.ctx, self.engine, self.guild):
            try:

                output_string = await save(
                    self.ctx, self.engine, self.bot, self.character.name, self.condition.title, modifier="",
                    guild=self.guild
                )
                await interaction.edit_original_response(content=output_string)
                await Tracker_Model.update_pinned_tracker()
                # await initiative.update_pinned_tracker(
                #     self.ctx, self.engine, self.bot, guild=self.guild
                # )
            except Exception:
                output_string = "Unable to process save, perhaps the condition was removed."
                await interaction.edit_original_response(content=output_string)
        else:
            output_string = "Roll your own save!"
            await interaction.edit_original_response(content=output_string)

        # await self.ctx.channel.send(output_string)