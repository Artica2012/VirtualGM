# imports
import asyncio
import logging
from datetime import datetime

import d20
import discord
from sqlalchemy import select, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Tracker import Tracker, get_init_list
from database_models import get_tracker, Global
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import advance_time, output_datetime, get_time
from utils.Char_Getter import get_character
from utils.utils import get_guild


async def get_EPF_Tracker(ctx, engine, init_list, bot, guild=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    return EPF_Tracker(ctx, engine, init_list, bot, guild=guild)


class EPF_Tracker(Tracker):
    def __init__(self, ctx, engine, init_list, bot, guild=None):
        super().__init__(ctx, engine, init_list, bot, guild)

    async def advance_initiative(self):
        if self.guild.block:
            await super().block_advance_initiative()
        else:
            await self.EPF_advance_initiative()

    async def EPF_advance_initiative(self):
        logging.info("EPF_advance_initiative")

        first_pass = False
        round = self.guild.round

        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            logging.info(f"BAI1: guild: {self.guild.id}")

            if self.guild.initiative is None:
                Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
                async with async_session() as session:
                    char_result = await session.execute(select(Tracker))
                    character = char_result.scalars().all()
                    logging.info("BAI2: characters")
                    init_pos = -1
                    round = 1
                    first_pass = True
                    for char in character:
                        await asyncio.sleep(0)
                        if char.init == 0:
                            await asyncio.sleep(0)
                            model = await get_character(char.name, self.ctx, guild=self.guild, engine=self.engine)
                            try:
                                roll = d20.roll(char.init_string)
                                await model.set_init(roll)
                            except ValueError:
                                model.set_init(0)
            else:
                init_pos = int(self.guild.initiative)

            await self.update()
            logging.info("BAI3: Updated")

            if self.guild.saved_order == "":
                current_character = await get_character(
                    self.init_list[0].name, self.ctx, engine=self.engine, guild=self.guild
                )
            else:
                current_character = await get_character(
                    self.guild.saved_order, self.ctx, engine=self.engine, guild=self.guild
                )

            # Process the conditions with the after trait (Flex = False) for the current character
            await self.init_con(current_character, False)

            # Advance the Turn
            # Check to make sure the init list hasn't changed, if so, correct it
            if not await self.init_integrity_check(init_pos, current_character) and not first_pass:
                logging.info("BAI6: init_itegrity failied")
                # print(f"integrity check was false: init_pos: {init_pos}")
                for pos, row in enumerate(self.init_list):
                    await asyncio.sleep(0)
                    if row.name == current_character:
                        init_pos = pos
                        # print(f"integrity checked init_pos: {init_pos}")

            # Increase the initiative positing by 1
            init_pos += 1  # increase the init position by 1
            # print(f"new init_pos: {init_pos}")
            # If we have exceeded the end of the list, then loop back to the beginning
            if init_pos >= len(self.init_list):  # if it has reached the end, loop back to the beginning
                init_pos = 0
                round += 1
                if self.guild.timekeeping:  # if timekeeping is enable on the server
                    logging.info("BAI7: timekeeping")
                    # Advance time time by the number of seconds in the guild.time column. Default is 6
                    # seconds ala D&D standard
                    await advance_time(self.ctx, self.engine, self.bot, second=self.guild.time, guild=self.guild)
                    await current_character.check_time_cc(self.bot)
                    logging.info("BAI8: cc checked")

            current_character = await get_character(
                self.init_list[init_pos].name, self.ctx, engine=self.engine, guild=self.guild
            )  # Update the new current_character

            # Delete the before conditions on the new current_character
            await self.init_con(current_character, True)

            # Write the updates to the database
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
                logging.info("BAI19: Writted")
            await self.update()
            return True
        except Exception as e:
            logging.error(f"block_advance_initiative: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "EPF_advance_initiative", e, self.bot)
                await report.report()

    async def block_get_tracker(self, selected: int, gm: bool = False):
        # print("PF2 Get Tracker")
        # Get the datetime
        datetime_string = ""

        logging.info(f"BGT1: Guild: {self.guild.id}")
        if self.guild.block and self.guild.initiative is not None:
            turn_list = await self.get_turn_list()
            block = True
        else:
            turn_list = []
            block = False
        logging.info(f"BGT2: round: {self.guild.round}")
        total_list = self.init_list
        active_length = len(total_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await self.get_inactive_list()
        if len(inactive_list) > 0:
            total_list.extend(inactive_list)
            # print(f'Total Length: {len(init_list)}')

        try:
            if self.guild.timekeeping:
                datetime_string = (
                    f" {await output_datetime(self.ctx, self.engine, self.bot, guild=self.guild)}\n__________________\n"
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
            if self.guild.round != 0:
                round_string = f"Round: {self.guild.round}"
            else:
                round_string = ""

            output_string = f"```{datetime_string}Initiative: {round_string}\n"

            for x, row in enumerate(total_list):
                logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
                character = await get_character(row.name, self.ctx, engine=self.engine, guild=self.guild)
                if len(total_list) > active_length and x == active_length:
                    output_string += "-----------------\n"  # Put in the divider

                condition_list = await character.conditions()

                await asyncio.sleep(0)
                sel_bool = False
                selector = ""

                # don't show an init if not in combat
                if row.init == 0 or row.active is False:
                    init_num = ""
                else:
                    init_num = f"{character.init}"

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
                if character.player or gm:
                    if row.temp_hp != 0:
                        string = (
                            f"{selector}  {init_num} {str(character.char_name).title()}:"
                            f" {character.current_hp}/{character.max_hp} ({character.temp_hp} Temp)"
                            f" AC:{character.ac_total}\n "
                        )
                    else:
                        string = (
                            f"{selector}  {init_num} {str(character.char_name).title()}:"
                            f" {character.current_hp}/{character.max_hp} AC: {character.ac_total}\n"
                        )
                else:
                    string = (
                        f"{selector}  {init_num} {str(character.char_name).title()}:"
                        f" {await character.calculate_hp()} \n"
                    )
                output_string += string

                for con_row in condition_list:
                    logging.info(f"BGT5: con_row in row[cc] {con_row.title} {con_row.id}")
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
                                        f"       {con_row.title}{'*' if con_row.action != '' else ''}:"
                                        f" {days_left} Days, {processed_minutes_left}:{processed_seconds_left}\n "
                                    )
                                else:
                                    if processed_hours_left != 0:
                                        con_string = (
                                            f"       {con_row.title}{'*' if con_row.action != '' else ''}:"
                                            f" {processed_hours_left}:{processed_minutes_left}:"
                                            f"{processed_seconds_left}\n"
                                        )
                                    else:
                                        con_string = (
                                            f"       {con_row.title}{'*' if con_row.action != '' else ''}:"
                                            f" {processed_minutes_left}:{processed_seconds_left}\n"
                                        )
                            else:
                                con_string = (
                                    f"       {con_row.title}{'*' if con_row.action != '' else ''}: {con_row.number}\n"
                                )
                        else:
                            con_string = f"       {con_row.title}{'*' if con_row.action != '' else ''}\n"

                    elif con_row.counter is True and sel_bool and row.player:
                        if con_row.number != 0:
                            con_string = (
                                f"       {con_row.title}{'*' if con_row.action != '' else ''}: {con_row.number}\n"
                            )
                        else:
                            con_string = f"       {con_row.title}{'*' if con_row.action != '' else ''}\n"
                    else:
                        con_string = ""
                    output_string += con_string
                    # print(output_string)
            output_string += "```"
            # print(output_string)
            return output_string
        except Exception as e:
            logging.info(f"block_get_tracker: {e}")
            return "ERROR"

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
                print(interaction.message.id)
                init_list = await get_init_list(self.ctx, self.engine, self.guild)
                for char in init_list:
                    Character_Model = await get_character(char.name, self.ctx, engine=self.engine, guild=self.guild)
                    await Character_Model.update()
                Tracker_model = EPF_Tracker(
                    self.ctx,
                    self.engine,
                    await get_init_list(self.ctx, self.engine, self.guild),
                    self.bot,
                    guild=self.guild,
                )
                await Tracker_model.update_pinned_tracker()
            except Exception as e:
                print(f"Error: {e}")
                logging.info(e)

    class NextButton(discord.ui.Button):
        def __init__(self, bot, guild=None):
            self.engine = get_asyncio_db_engine(
                user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA
            )
            self.bot = bot
            self.guild = guild
            super().__init__(style=discord.ButtonStyle.primary, emoji="➡️")

        async def callback(self, interaction: discord.Interaction):
            try:
                advance = True
                if self.guild.block:
                    advance = False
                    # print("Block")
                    # print(self.guild.block_data)
                    if interaction.user.id in self.guild.block_data:
                        new_block = self.guild.block_data.copy()
                        new_block.remove(interaction.user.id)

                        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                        async with async_session() as session:
                            result = await session.execute(select(Global).where(Global.id == self.guild.id))
                            guild = result.scalars().one()
                            guild.block_data = new_block
                            await session.commit()
                        if len(new_block) == 0:
                            advance = True
                        else:
                            await interaction.response.send_message(
                                (
                                    "Turn Marked Complete. Initiative Will Advance once all players have marked"
                                    " themselves complete"
                                ),
                                ephemeral=True,
                            )
                        if interaction.user.id == int(self.guild.gm):
                            advance = True
                    else:
                        advance = False
                        await interaction.response.send_message(
                            "Either it is not your turn, or you have already marked yourself complete", ephemeral=True
                        )
                if advance:
                    await interaction.response.send_message("Initiative Advanced", ephemeral=True)
                    Tracker_Model = EPF_Tracker(
                        None,
                        self.engine,
                        await get_init_list(None, self.engine, self.guild),
                        self.bot,
                        guild=self.guild,
                    )
                    await Tracker_Model.next()
                else:
                    Tracker_Model = EPF_Tracker(
                        None,
                        self.engine,
                        await get_init_list(None, self.engine, self.guild),
                        self.bot,
                        guild=self.guild,
                    )
                    await Tracker_Model.update_pinned_tracker()
            except Exception as e:
                print(f"Error: {e}")
                logging.info(e)
