import asyncio
import logging
from datetime import datetime

import discord
from sqlalchemy import select, true, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import database_operations
from Base.Tracker import Tracker
from database_models import get_condition, get_tracker, Global
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, get_time, advance_time
from utils.Char_Getter import get_character
from utils.utils import get_guild


async def get_RED_Tracker(ctx, engine, init_list, bot, guild=None):
    if engine is None:
        engine = database_operations.engine
    guild = await get_guild(ctx, guild)
    init_list = await get_init_list(ctx, engine, guild=guild)
    return RED_Tracker(ctx, engine, init_list, bot, guild=guild)


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
                .order_by(Tracker.tie_breaker.desc())
                .order_by(Tracker.id.desc())
            )
            init_list = result.scalars().all()
            logging.info("GIL: Init list gotten")
            # print(init_list)
        return init_list

    except Exception:
        logging.error("error in get_init_list")
        return []


class RED_Tracker(Tracker):
    def __int__(self, ctx, engine, init_list, bot, guild=None):
        super().__init__(ctx, engine, init_list, bot)
        self.guild = guild

    async def get_init_list(self, ctx: discord.ApplicationContext, engine, guild=None):
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
                    .order_by(Tracker.tie_breaker.desc())
                    .order_by(Tracker.id.desc())
                )
                init_list = result.scalars().all()
                logging.info("GIL: Init list gotten")
                # print(init_list)
            return init_list

        except Exception:
            logging.error("error in get_init_list")
            return []

    async def block_advance_initiative(self):
        logging.info("advance_initiative")

        block_done = False
        turn_list = []
        first_pass = False
        round = self.guild.round

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
                        # print(model.char_name, model.init)
                        if model.init == 0:
                            await asyncio.sleep(0)
                            try:
                                await model.set_init(None)
                                # print(model.init, model.tie_breaker)
                            except Exception:
                                await model.set_init(0)

                else:
                    init_pos = int(self.guild.initiative)

            await self.update()
            logging.info("BAI3: updated")

            if self.guild.saved_order == "":
                current_character = await get_character(
                    self.init_list[0].name, self.ctx, engine=self.engine, guild=self.guild
                )
            else:
                current_character = await get_character(
                    self.guild.saved_order, self.ctx, engine=self.engine, guild=self.guild
                )

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
                    if not await self.init_integrity_check(init_pos, current_character.char_name) and not first_pass:
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
                            await current_character.check_time_cc()
                            logging.info("BAI8: cc checked")

                # Decrement the conditions
                await self.init_con(current_character, None)

                if not self.guild.block:  # if not in block initiative, decrement the conditions at the end of the turn
                    logging.info("BAI14: Not Block")
                    # print("Not guild.block")
                    # if its not, set the init position to the position of the current character before advancing it
                    if not await self.init_integrity_check(init_pos, current_character.char_name) and not first_pass:
                        logging.info("BAI15: Integrity check failed")
                        # print(f"integrity check was false: init_pos: {init_pos}")
                        for pos, row in enumerate(self.init_list):
                            await asyncio.sleep(0)
                            if row.name == current_character.char_name:
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
                            # await current_character.check_time_cc(self.bot)
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
                current_character = await get_character(
                    self.init_list[init_pos].name, self.ctx, engine=self.engine, guild=self.guild
                )
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

    async def efficient_block_get_tracker(
        self, selected: int, gm: bool = False
    ):  # Probably should rename this eventually
        logging.info("generic_block_get_tracker")
        # Get the datetime
        datetime_string = ""
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        # Get the turn List for Block Initiative
        if self.guild.block and self.guild.initiative is None:  # Should this be initiative is not None?
            turn_list = await self.get_turn_list()
            block = True
        else:
            block = False
        logging.info(f"BGT2: round: {self.guild.round}")

        # Code for appending the inactive list onto the init_list
        total_list = await self.get_init_list(self.ctx, self.engine, guild=self.guild)
        active_length = len(total_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await self.get_inactive_list()
        if len(inactive_list) > 0:
            total_list.extend(inactive_list)
            # print(f'Total Length: {len(init_list)}')

        # Generate the data_time string if timekeeper is active
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

            # if round = 0, were not in initiative, and act accordingly
            if self.guild.round != 0:
                round_string = f"Round: {self.guild.round}"
            else:
                round_string = ""

            output_string = f"```{datetime_string}Initiative: {round_string}\n"
            gm_output_string = f"```{datetime_string}Initiative: {round_string}\n"
            # Iterate through the init list
            for x, row in enumerate(total_list):
                character = await get_character(row.name, self.ctx, engine=self.engine, guild=self.guild)
                logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
                # If there is an inactive list, and this is at the transition, place the line marker
                if len(total_list) > active_length and x == active_length:
                    output_string += "-----------------\n"  # Put in the divider
                    gm_output_string += "-----------------\n"

                # Get all of the visible condition for the character
                async with async_session() as session:
                    result = await session.execute(
                        select(Condition)
                        .where(Condition.character_id == character.id)
                        .where(Condition.visible == true())
                    )
                    condition_list = result.scalars().all()

                await asyncio.sleep(0)  # ensure the loop doesn't lock the bot in case of an error
                sel_bool = False
                selector = "  "

                # don't show an init if not in combat
                # print(character.char_name, character.init)
                if character.init == 0 or character.active is False:
                    init_num = ""
                else:
                    if character.init <= 9:
                        init_num = f" {character.init}"
                    else:
                        init_num = f"{character.init}"

                if character.net_status:
                    net_mod = "(NET) "
                else:
                    net_mod = ""

                if block:
                    for (
                        char
                    ) in (
                        turn_list
                    ):  # ignore this error, turn list is gotten if block is true, so this will always apply
                        # print(f'character.id = {character.id}')
                        if character.id == char.id:
                            sel_bool = True
                else:
                    if x == selected:
                        sel_bool = True

                # print(f"{row['name']}: x: {x}, selected: {selected}")

                if sel_bool:
                    selector = ">>"
                if character.temp_hp != 0:
                    string = (
                        f"{selector}  {init_num} {net_mod}{str(character.char_name).title()}:"
                        f"     {character.current_hp}/{character.max_hp} ({character.temp_hp} Temp)\n"
                        f"{character.armor_output_string if not  character.net_status else ''}"
                    )
                else:
                    string = (
                        f"{selector}  {init_num} {net_mod}{str(character.char_name).title()}:"
                        f"     {character.current_hp}/{character.max_hp}\n"
                        f"{character.armor_output_string if not  character.net_status else ''}"
                    )
                gm_output_string += string
                if character.player:
                    output_string += string
                else:
                    string = (
                        f"{selector}  {init_num} {net_mod}{str(character.char_name).title()}:"
                        f"     {await character.calculate_hp()} \n"
                    )
                    output_string += string

                for con_row in condition_list:
                    logging.info(f"BGT5: con_row in condition list {con_row.title} {con_row.id}")
                    # print(con_row)
                    await asyncio.sleep(0)

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
                                        f"       {con_row.title}:"
                                        f" {processed_hours_left}:{processed_minutes_left}:"
                                        f"{processed_seconds_left}\n"
                                    )
                                else:
                                    con_string = (
                                        f"       {con_row.title}: {processed_minutes_left}:{processed_seconds_left}\n"
                                    )
                        else:
                            con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = f"       {con_row.title}\n"

                    gm_output_string += con_string
                    if con_row.counter is True and sel_bool and row.player:
                        output_string += con_string
                    elif not con_row.counter:
                        output_string += con_string

            output_string += "```"
            gm_output_string += "```"
            # print(output_string)
            return {"tracker": output_string, "gm_tracker": gm_output_string}
        except Exception as e:
            logging.info(f"block_get_tracker 2: {e}")
            return "ERROR"

    class InitRefreshButton(discord.ui.Button):
        def __init__(self, ctx: discord.ApplicationContext, bot, guild=None):
            self.ctx = ctx
            self.engine = database_operations.engine
            self.bot = bot
            self.guild = guild
            super().__init__(style=discord.ButtonStyle.primary, emoji="🔁")

        async def callback(self, interaction: discord.Interaction):
            try:
                await interaction.response.send_message("Refreshed", ephemeral=True)
                # print(interaction.message.id)
                Tracker_model = RED_Tracker(
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

    class NextButton(discord.ui.Button):
        def __init__(self, bot, guild=None):
            self.engine = database_operations.engine
            self.bot = bot
            self.guild = guild
            super().__init__(
                style=discord.ButtonStyle.primary, emoji="➡️" if not guild.block or len(guild.block_data) < 2 else "✔"
            )

        async def callback(self, interaction: discord.Interaction):
            try:
                Tracker_Model = RED_Tracker(
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
