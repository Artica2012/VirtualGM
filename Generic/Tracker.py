# imports
import asyncio
import logging
import os

import d20
import discord
from dotenv import load_dotenv
from sqlalchemy import select, true, or_, false
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime

import initiative
import ui_components
from database_models import get_tracker, Global, get_condition
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import advance_time, output_datetime, get_time
from utils.utils import get_guild
from utils.Char_Getter import get_character

from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA


async def get_init_list(ctx: discord.ApplicationContext, engine, guild=None):
    logging.info("get_init_list")
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
                    .order_by(Tracker.id.desc())
            )
            init_list = result.scalars().all()
            logging.info("GIL: Init list gotten")
            # print(init_list)
        return init_list

    except Exception:
        logging.error("error in get_init_list")
        return []


class Tracker():
    def __init__(self, ctx, engine, init_list, bot, guild=None):
        self.ctx = ctx
        self.engine = engine
        self.init_list = init_list
        self.guild = guild
        self.bot = bot

    async def next(self):
        await self.advance_initiative()
        await self.block_post_init()

    async def update(self):
        self.guild = await get_guild(self.ctx, self.guild, refresh=True)
        self.init_list = await get_init_list(self.ctx, self.engine, guild=self.guild)

    async def init_integrity_check(self, init_pos: int, current_character: str):
        logging.info("init_integrity_check")
        # print(guild.id)
        # print(init_list)
        try:
            if self.init_list[init_pos].name == current_character:
                return True
            else:
                return False
        except IndexError:
            return False
        except Exception as e:
            logging.error(f"init_integrity_check: {e}")
            return False

    async def init_integrity(self):
        logging.info("Checking Initiative Integrity")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.id == self.guild.id))
            guild = result.scalars().one()

            if guild.initiative is not None:
                if not await self.init_integrity_check(guild.initiative, guild.saved_order):
                    logging.info("Integrity Check Failed")
                    logging.info(f"Integrity Info: Saved_Order {guild.saved_order}, Init Pos={guild.initiative}")
                    for pos, row in enumerate(self.init_list):
                        if row.name == guild.saved_order:
                            logging.info(f"name: {row.name}, saved_order: {guild.saved_order}")
                            guild.initiative = pos
                            logging.info(f"Pos: {pos}")
                            logging.info(f"New Init_pos: {guild.initiative}")
                            break  # once its fixed, stop the loop because its done
            await session.commit()

    async def advance_initiative(self):
        return await self.block_advance_initiative()

    async def block_advance_initiative(self):
        logging.info(f"advance_initiative")

        block_done = False
        turn_list = []
        first_pass = False
        round=self.guild.round

        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            logging.info(f"BAI1: guild: {self.guild.id}")

            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                char_result = await session.execute(select(Tracker))
                character = char_result.scalars().all()
                logging.info("BAI2: characters")

                # Roll initiative if this is the start of init
                # print(f"guild.initiative: {guild.initiative}")
                if self.guild.initiative is None:
                    init_pos = -1
                    round = 1
                    first_pass = True
                    for char in character:
                        await asyncio.sleep(0)
                        model = await get_character(char.name, self.ctx, guild=self.guild, engine=self.engine)
                        if model.init == 0:
                            await asyncio.sleep(0)
                            try:
                                roll = d20.roll(char.init_string)
                                await model.set_init(roll)
                            except:
                                await model.set_init(0)
                else:
                    init_pos = int(self.guild.initiative)

            await self.update()
            logging.info("BAI3: updated")

            if self.guild.saved_order == "":
                current_character = await get_character(self.init_list[0].name, self.ctx, engine=self.engine,
                                                        guild=self.guild)
            else:
                current_character = await get_character(self.guild.saved_order, self.ctx, engine=self.engine,
                                                        guild=self.guild)

            # Record the initial to break an infinite loop
            iterations = 0
            logging.info(f"BAI4: iteration: {iterations}")

            while not block_done:
                # make sure that the current character is at the same place in initiative as it was before
                # decrement any conditions with the decrement flag

                if self.guild.block:  # if in block initiative, decrement conditions at the beginning of the turn
                    # if its not, set the init position to the position of the current character before advancing it
                    # print("Yes guild.block")
                    logging.info(f"BAI5: guild.block: {self.guild.block}")
                    if (
                            not await self.init_integrity_check(init_pos, current_character.char_name)
                            and not first_pass
                    ):
                        logging.info("BAI6: init_itegrity failied")
                        for pos, row in enumerate(self.init_list):
                            await asyncio.sleep(0)
                            if row.name == current_character.char_name:
                                init_pos = pos
                                break
                    init_pos += 1  # increase the init position by 1

                    if init_pos >= len(self.init_list):  # if it has reached the end, loop back to the beginning
                        init_pos = 0
                        round += 1
                        if self.guild.timekeeping:  # if timekeeping is enable on the server
                            logging.info("BAI7: timekeeping")
                            # Advance time time by the number of seconds in the guild.time column. Default is 6
                            # seconds ala D&D standard
                            await advance_time(self.ctx, self.engine, None, second=self.guild.time, guild=self.guild)
                            await current_character.check_time_cc(self.bot)
                            logging.info("BAI8: cc checked")

                # Decrement the conditions
                await self.init_con(current_character, None)

                if not self.guild.block:  # if not in block initiative, decrement the conditions at the end of the turn
                    logging.info("BAI14: Not Block")
                    # print("Not guild.block")
                    # if its not, set the init position to the position of the current character before advancing it
                    if (
                            not await self.init_integrity_check(init_pos, current_character.char_name)
                            and not first_pass
                    ):
                        logging.info("BAI15: Integrity check failed")
                        # print(f"integrity check was false: init_pos: {init_pos}")
                        for pos, row in enumerate(self.init_list):
                            await asyncio.sleep(0)
                            if row.name == current_character:
                                init_pos = pos
                                # print(f"integrity checked init_pos: {init_pos}")
                    init_pos += 1  # increase the init position by 1
                    # print(f"new init_pos: {init_pos}")
                    if init_pos >= len(self.init_list):  # if it has reached the end, loop back to the beginning
                        init_pos = 0
                        round += 1
                        if self.guild.timekeeping:  # if timekeeping is enable on the server
                            # Advance time time by the number of seconds in the guild.time column. Default is 6
                            # seconds ala D&D standard
                            await advance_time(self.ctx, self.engine, None, second=self.guild.time, guild=self.guild)
                            await current_character.check_time_cc(self.bot)
                            logging.info("BAI16: cc checked")

                            # block initiative loop
                # check to see if the next character is player vs npc
                # print(init_list)
                # print(f"init_pos: {init_pos}, len(init_list): {len(init_list)}")
                if init_pos >= len(self.init_list) - 1:
                    # print(f"init_pos: {init_pos}")
                    if self.init_list[init_pos].player != self.init_list[0].player:
                        block_done = True
                elif self.init_list[init_pos].player != self.init_list[init_pos + 1].player:
                    block_done = True
                if not self.guild.block:
                    block_done = True

                turn_list.append(self.init_list[init_pos].name)
                current_character = await get_character(self.init_list[init_pos].name, self.ctx, engine=self.engine,
                                                        guild=self.guild)
                iterations += 1
                if iterations >= len(self.init_list):  # stop an infinite loop
                    block_done = True

                # print(turn_list)

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
                logging.info(f"BAI17: guild updated: {guild.id}")
                guild.initiative = init_pos  # set it
                guild.round = round
                guild.saved_order = str(self.init_list[init_pos].name)
                logging.info(f"BAI18: saved order: {guild.saved_order}")
                await session.commit()
                logging.info("BAI19: Written")
            await self.update()
            return True
        except Exception as e:
            logging.error(f"block_advance_initiative: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "block_advance_initiative", e, self.bot)
                await report.report()

    # This is the code which check, decrements and removes conditions for the init next turn.
    async def init_con(self, current_character, before: bool):
        logging.info(f"{current_character}, {before}")
        logging.info("Decrementing Conditions")

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        # Run through the conditions on the current character

        try:
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
            # con = await get_condition_table(ctx, metadata, engine)
            async with async_session() as session:
                if before is not None:
                    char_result = await session.execute(
                        select(Condition)
                            .where(Condition.character_id == current_character.id)
                            .where(Condition.flex == before)
                            .where(Condition.auto_increment == true())
                    )
                else:
                    char_result = await session.execute(
                        select(Condition)
                            .where(Condition.character_id == current_character.id)
                            .where(Condition.auto_increment == true())
                    )
                con_list = char_result.scalars().all()
                logging.info("BAI9: condition's retrieved")
                # print("First Con List")

            for con_row in con_list:
                logging.info(f"BAI10: con_row: {con_row.title} {con_row.id}")
                await asyncio.sleep(0)
                if not con_row.time:
                    if con_row.number >= 2:
                        await current_character.edit_cc(con_row.title, con_row.number-1)
                    else:
                        await current_character.delete_cc(con_row.title)
                        if self.ctx is not None:
                            await self.ctx.channel.send(f"{con_row.title} removed from {current_character.char_name}")
                        elif self.bot is not None:
                            tracker_channel = self.bot.get_channel(self.guild.tracker_channel)
                            await tracker_channel.send(f"{con_row.title} removed from {current_character.char_name}")
                else:
                    await current_character.check_time_cc(bot=self.bot)

        except Exception as e:
            logging.error(f"block_advance_initiative: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "init_con", e, self.bot)
                await report.report()

    async def get_inactive_list(self):
        logging.info("get_inactive_list")
        Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Tracker)
                        .where(Tracker.active == false())
                        .order_by(Tracker.init.desc())
                        .order_by(Tracker.id.desc())
                )
                init_list = result.scalars().all()
                logging.info("GIL: Init list gotten")
                # print(init_list)
            return init_list
        except Exception:
            logging.error("error in get_init_list")
            return []

    async def block_get_tracker(self, selected: int, gm: bool = False): # Probably should rename this eventually
        logging.info("generic_block_get_tracker")
        # Get the datetime
        datetime_string = ""
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        # Get the turn List for Block Initiative
        if self.guild.block and self.guild.initiative is None:  #Should this be initiative is not None?
            turn_list = await self.get_turn_list()
            block = True
        else:
            block = False
        logging.info(f"BGT2: round: {self.guild.round}")

        # Code for appending the inactive list onto the init_list
        total_list = self.init_list
        active_length = len(total_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await self.get_inactive_list()
        if len(inactive_list) > 0:
            total_list.extend(inactive_list)
            # print(f'Total Length: {len(init_list)}')

        # Generate the data_time string if timekeeper is active
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

            # if round = 0, were not in initiative, and act accordingly
            if self.guild.round != 0:
                round_string = f"Round: {self.guild.round}"
            else:
                round_string = ""

            output_string = f"```{datetime_string}Initiative: {round_string}\n"
            # Iterate through the init list
            for x, row in enumerate(total_list):
                character = await get_character(row.name, self.ctx, engine=self.engine, guild=self.guild)
                logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
                # If there is an inactive list, and this is at the transition, place the line marker
                if len(total_list) > active_length and x == active_length:
                    output_string += "-----------------\n"  # Put in the divider

                # Get all of the visible condition for the character
                async with async_session() as session:
                    result = await session.execute(
                        select(Condition).where(Condition.character_id == character.id).where(Condition.visible == true())
                    )
                    condition_list = result.scalars().all()

                await asyncio.sleep(0)  # ensure the loop doesn't lock the bot in case of an error
                sel_bool = False
                selector = ""

                # don't show an init if not in combat
                if character.init == 0 or character.active is False:
                    init_num = ""
                else:
                    init_num = f"{character.init}"

                if block:
                    for (
                            char
                    ) in turn_list:  # ignore this error, turn list is gotten if block is true, so this will always apply
                        # print(f'character.id = {character.id}')
                        if character.id == char.id:
                            sel_bool = True
                else:
                    if x == selected:
                        sel_bool = True

                # print(f"{row['name']}: x: {x}, selected: {selected}")

                if sel_bool:
                    selector = ">>"
                if character.player or gm:
                    if character.temp_hp != 0:
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
                    logging.info(f"BGT5: con_row in condition list {con_row.title} {con_row.id}")
                    # print(con_row)
                    await asyncio.sleep(0)
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
                                        f" {processed_minutes_left}:{processed_seconds_left}\n "
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

            output_string += "```"
            # print(output_string)
            return output_string
        except Exception as e:
            logging.info(f"block_get_tracker 2: {e}")
            return ""

    # Note: Works backwards
    # This is the turn list, a list of all of characters that are part of the turn in block initiative
    async def get_turn_list(self):
        logging.info("get_turn_list")
        turn_list = []
        block_done = False
        try:
            logging.info(f"GTL1: guild: {self.guild.id}")
            iteration = 0
            init_pos = self.guild.initiative
            # print(f"init_pos: {init_pos}")
            # print(init_pos)
            length = len(self.init_list)
            while not block_done:
                turn_list.append(self.init_list[init_pos])
                # print(f"init_pos: {init_pos}, turn_list: {turn_list}")
                player_status = self.init_list[init_pos].player
                if init_pos == 0:
                    if player_status != self.init_list[length - 1].player:
                        block_done = True
                else:
                    if player_status != self.init_list[init_pos - 1].player:
                        block_done = True

                init_pos -= 1
                if init_pos < 0:
                    if self.guild.round != 1:  # Don't loop back to the end on the first round
                        init_pos = length - 1
                    else:
                        block_done = True
                iteration += 1
                if iteration >= length:
                    block_done = True
            logging.info(f"GTL2 {turn_list}")
            return turn_list
        except Exception as e:
            logging.warning(f"get_turn_list: {e}")
            return []

    # Post a new initiative tracker and updates the pinned trackers
    async def block_post_init(self):
        logging.info(f"block_post_init")
        # Query the initiative position for the tracker and post it

        try:
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
            except Exception as e:
                logging.error(f'post_init: {e}')
                ping_string = ""

            # Check for systems:

            view = discord.ui.View(timeout=None)
            view.add_item(ui_components.InitRefreshButton(self.ctx, self.bot, guild=self.guild))
            view.add_item(ui_components.NextButton(self.bot, guild=self.guild))
            # Always post the tracker to the player channel
            if self.ctx is not None:
                if self.ctx.channel.id == self.guild.tracker_channel:
                    tracker_msg = await self.ctx.send_followup(f"{tracker_string}\n{ping_string}", view=view)
                else:
                    await self.bot.get_channel(self.guild.tracker_channel).send(f"{tracker_string}\n{ping_string}", view=view)
                    tracker_msg = await self.ctx.send_followup("Initiative Advanced.")
                    logging.info("BPI5")
            else:
                tracker_msg = await self.bot.get_channel(self.guild.tracker_channel).send(
                    f"{tracker_string}\n{ping_string}", view=view
                )
                logging.info("BPI5 Guild")

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
                try:
                    if guild.last_tracker is not None:
                        tracker_channel = self.bot.get_channel(guild.tracker_channel)
                        old_tracker_msg = await tracker_channel.fetch_message(guild.last_tracker)
                        await old_tracker_msg.edit(view=None)
                except Exception as e:
                    logging.warning(e)
                guild.last_tracker = tracker_msg.id
                await session.commit()
                await self.update()
        except NoResultFound:
            if self.ctx is not None:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
        except Exception as e:
            logging.error(f"block_post_init: {e}")
            if self.ctx is not None:
                report = ErrorReport(self.ctx, "block_post_init", e, self.bot)
                await report.report()

    # Updates the active initiative tracker (not the pinned tracker)
    async def update_pinned_tracker(self):
        logging.info(f"update_pinned_tracker")

        # Query the initiative position for the tracker and post it
        # try:
        logging.info(f"BPI1: guild: {self.guild.id}")


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
        if self.guild.last_tracker is not None:
            view.add_item(ui_components.InitRefreshButton(self.ctx, self.bot, guild=self.guild))
            view.add_item((ui_components.NextButton(self.bot, guild=self.guild)))
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

        # except NoResultFound:
        #     await self.ctx.channel.send(error_not_initialized, delete_after=30)
        # except Exception as e:
        #     logging.error(f"update_pinned_tracker: {e}")
        #     report = ErrorReport(self.ctx, "update_pinned_tracker", e, self.bot)
        #     await report.report()


