import asyncio
import logging
from datetime import datetime

import discord
from sqlalchemy.exc import NoResultFound

from Systems.Base.Tracker import Tracker, get_init_list
from Backend.Database.database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Backend.Database.engine import engine
from Backend.Database.database_operations import get_asyncio_db_engine
from Backend.utils.error_handling_reporting import error_not_initialized, ErrorReport
from Backend.utils.time_keeping_functions import output_datetime, get_time
from Backend.utils.Char_Getter import get_character
from Backend.utils.utils import get_guild


async def get_STF_Tracker(ctx, engine, init_list, bot, guild=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    return STF_Tracker(ctx, engine, init_list, bot, guild=guild)


class STF_Tracker(Tracker):
    def __init__(self, ctx, engine, init_list, bot, guild=None):
        super().__init__(ctx, engine, init_list, bot, guild)

    async def efficient_block_get_tracker(self, selected: int, gm: bool = False):
        # print("PF2 Get Tracker")
        # Get the datetime
        datetime_string = ""

        logging.info(f"STF BGT1: Guild: {self.guild.id}")
        if self.guild.block and self.guild.initiative is not None:
            turn_list = await self.get_turn_list()
            block = True
        else:
            turn_list = []
            block = False
        logging.info(f"BGT2: round: {self.guild.round}")
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
            gm_output_string = f"```{datetime_string}Initiative: {round_string}\n"

            for x, row in enumerate(total_list):
                logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
                character = await get_character(row.name, self.ctx, engine=self.engine, guild=self.guild)
                if len(total_list) > active_length and x == active_length:
                    output_string += "-----------------\n"  # Put in the divider
                    gm_output_string += "-----------------\n"  # Put in the divider

                condition_list = await character.conditions()

                await asyncio.sleep(0)
                sel_bool = False
                selector = "  "

                # don't show an init if not in combat
                if row.init == 0 or row.active is False:
                    init_num = ""
                else:
                    if character.init <= 9:
                        init_num = f" {character.init}"
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

                if row.temp_hp != 0:
                    string = (
                        f"{selector}  {init_num} {str(character.char_name).title()}:"
                        f" H:{character.current_hp}/{character.max_hp} S:{character.current_stamina}/"
                        f"{character.max_stamina} (Temp:"
                        f" {character.temp_hp}) \n     KAC:{character.kac}, EAC: {character.eac}, RP:"
                        f" {character.current_resolve}\n"
                    )
                else:
                    string = (
                        f"{selector}  {init_num} {str(character.char_name).title()}:"
                        f" H:{character.current_hp}/{character.max_hp} S:{character.current_stamina}/"
                        f"{character.max_stamina} \n"
                        f"     KAC:{character.kac}, EAC: {character.eac}, RP: {character.current_resolve}\n"
                    )
                gm_output_string += string
                if character.player:
                    output_string += string
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
                    elif con_row.number != 0:
                        con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = f"       {con_row.title}\n"

                    gm_output_string += con_string

                    if con_row.counter is True and sel_bool and row.player:
                        output_string += con_string
                    elif not con_row.counter:
                        output_string += con_string
                    # print(output_string)
            output_string += "```"
            gm_output_string += "```"
            # print(output_string)
            return {"tracker": output_string, "gm_tracker": gm_output_string}
        except Exception as e:
            logging.info(f"block_get_tracker: {e}")
            return "ERROR"

    class InitRefreshButton(discord.ui.Button):
        def __init__(self, ctx: discord.ApplicationContext, bot, guild=None):
            self.ctx = ctx
            self.engine = engine
            self.bot = bot
            self.guild = guild
            super().__init__(style=discord.ButtonStyle.primary, emoji="🔁")

        async def callback(self, interaction: discord.Interaction):
            try:
                await interaction.response.send_message("Refreshed", ephemeral=True)
                # print(interaction.message.id)
                init_list = await get_init_list(self.ctx, self.engine, self.guild)
                for char in init_list:
                    Character_Model = await get_character(char.name, self.ctx, engine=self.engine, guild=self.guild)
                    await Character_Model.update()
                Tracker_model = STF_Tracker(
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
            self.engine = engine
            self.bot = bot
            self.guild = guild
            super().__init__(
                style=discord.ButtonStyle.primary, emoji="➡️" if not guild.block or len(guild.block_data) < 2 else "✔"
            )

        async def callback(self, interaction: discord.Interaction):
            try:
                Tracker_Model = Tracker(
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
