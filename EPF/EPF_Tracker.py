# imports
import asyncio
import logging

import d20
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_tracker, Global
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from time_keeping_functions import advance_time
from utils.utils import get_guild
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Base.Tracker import Tracker
from utils.Char_Getter import get_character


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
                current_character = await get_character(self.init_list[0].name, self.ctx, engine=self.engine,
                                                        guild=self.guild)
            else:
                current_character = await get_character(self.guild.saved_order, self.ctx, engine=self.engine,
                                                        guild=self.guild)

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

            current_character = await get_character(self.init_list[init_pos].name, self.ctx, engine=self.engine, guild=self.guild)  # Update the new current_character

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




