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


async def get_PF2_Tracker(ctx, engine, init_list, bot, guild=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    return PF2_Tracker(ctx, engine, init_list, bot, guild=guild)


class PF2_Tracker(Tracker):
    def __init__(self, ctx, init_list, bot, engine=None, guild=None):
        super().__init__(ctx, init_list, bot, engine, guild)

    # Builds the tracker string. Updated to work with block initiative
    async def block_get_tracker(self, selected: int, gm: bool = False):
        # print("PF2 Get Tracker")
        # Get the datetime
        datetime_string = ""
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)


        logging.info(f"BGT1: Guild: {guild.id}")
        if guild.block and guild.initiative is not None:
            turn_list = await initiative.get_turn_list(ctx, engine, bot, guild=guild)
            block = True
        else:
            turn_list = []
            block = False
        logging.info(f"BGT2: round: {guild.round}")

        active_length = len(init_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await initiative.get_inactive_list(ctx, engine, guild)
        if len(inactive_list) > 0:
            init_list.extend(inactive_list)
            # print(f'Total Length: {len(init_list)}')

        try:
            if await check_timekeeper(ctx, engine, guild=guild):
                datetime_string = f" {await output_datetime(ctx, engine, bot, guild=guild)}\n________________________\n"
        except NoResultFound:
            if ctx is not None:
                await ctx.channel.send(error_not_initialized, delete_after=30)
            logging.info("Channel Not Set Up")
        except Exception as e:
            logging.error(f"get_tracker: {e}")
            report = ErrorReport(ctx, "get_tracker", e, bot)
            await report.report()

        try:
            Condition = await get_condition(ctx, engine, id=guild.id)

            if guild.round != 0:
                round_string = f"Round: {guild.round}"
            else:
                round_string = ""

            output_string = f"```{datetime_string}Initiative: {round_string}\n"

            for x, row in enumerate(init_list):
                logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
                if len(init_list) > active_length and x == active_length:
                    output_string += "-----------------\n"  # Put in the divider
                async with async_session() as session:
                    result = await session.execute(
                        select(Condition).where(Condition.character_id == row.id).where(Condition.visible == true())
                    )
                    condition_list = result.scalars().all()
                try:
                    async with async_session() as session:
                        result = await session.execute(
                            select(Condition.number)
                                .where(Condition.character_id == row.id)
                                .where(Condition.visible == false())
                                .where(Condition.title == "AC")
                        )
                        armor_class = result.scalars().one()
                        # print(armor_class.number)
                        ac = armor_class
                except Exception:
                    ac = ""

                await asyncio.sleep(0)
                sel_bool = False
                selector = ""

                # don't show an init if not in combat
                if row.init == 0 or row.active is False:
                    init_string = ""
                else:
                    init_string = f"{row.init}"

                if block:
                    for character in turn_list:
                        if row.id == character.id:
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
                            f"{selector}  {init_string} {str(row.name).title()}:"
                            f" {row.current_hp}/{row.max_hp} ({row.temp_hp}) Temp AC:{ac}\n "
                        )
                    else:
                        string = (
                            f"{selector}  {init_string} {str(row.name).title()}: {row.current_hp}/{row.max_hp} AC: {ac}\n"
                        )
                else:
                    hp_string = await initiative.calculate_hp(row.current_hp, row.max_hp)
                    string = f"{selector}  {init_string} {str(row.name).title()}: {hp_string} \n"
                output_string += string

                for con_row in condition_list:
                    logging.info(f"BGT5: con_row in row[cc] {con_row.title} {con_row.id}")
                    # print(con_row)
                    await asyncio.sleep(0)
                    if gm or not con_row.counter:
                        if con_row.number is not None and con_row.number > 0:
                            if con_row.time:
                                time_stamp = datetime.fromtimestamp(con_row.number)
                                current_time = await get_time(ctx, engine, guild=guild)
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
                        if con_row.number != 0:
                            con_string = f"       {con_row.title}: {con_row.number}\n"
                        else:
                            con_string = f"       {con_row.title}\n"
                    else:
                        con_string = ""
                    output_string += con_string
                    # print(output_string)
            output_string += "```"
            # print(output_string)
            await engine.dispose()
            return output_string
        except Exception as e:
            logging.info(f"block_get_tracker: {e}")
            if ctx is not None:
                report = ErrorReport(ctx, pf2_get_tracker.__name__, e, bot)
                await report.report()


