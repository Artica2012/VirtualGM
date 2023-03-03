# imports
import asyncio
import logging
import os

import d20
import discord
from dotenv import load_dotenv
from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import initiative
from database_models import get_tracker, Global, get_condition
from time_keeping_functions import advance_time
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
        await engine.dispose()
        return init_list

    except Exception:
        logging.error("error in get_init_list")
        return []


class Tracker():
    def __init__(self, ctx, engine, init_list, guild=None):
        self.ctx = ctx
        self.engine = engine
        self.init_list = init_list
        self.guild = guild

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
        logging.info(f"advance_initiative")

        block_done = False
        turn_list = []
        first_pass = False

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
                    self.guild.round = 1
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
                current_character = self.init_list[0].name
            else:
                current_character = self.guild.saved_order
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
                            not await self.init_integrity_check(init_pos, current_character)
                            and not first_pass
                    ):
                        logging.info("BAI6: init_itegrity failied")
                        for pos, row in enumerate(self.init_list):
                            await asyncio.sleep(0)
                            if row.name == current_character:
                                init_pos = pos
                                break
                    init_pos += 1  # increase the init position by 1

                    if init_pos >= len(self.init_list):  # if it has reached the end, loop back to the beginning
                        init_pos = 0
                        self.guild.round += 1
                        if self.guild.timekeeping:  # if timekeeping is enable on the server
                            logging.info("BAI7: timekeeping")
                            # Advance time time by the number of seconds in the guild.time column. Default is 6
                            # seconds ala D&D standard
                            await advance_time(self.ctx, self.engine, None, second=self.guild.time, guild=self.guild)
                            await check_cc(ctx, engine, bot, guild=guild)
                            logging.info("BAI8: cc checked")

                # Decrement the conditions
                await init_con(ctx, engine, bot, current_character, None, guild)

                if not guild.block:  # if not in block initiative, decrement the conditions at the end of the turn
                    logging.info("BAI14: Not Block")
                    # print("Not guild.block")
                    # if its not, set the init position to the position of the current character before advancing it
                    if (
                            not await init_integrity_check(ctx, init_pos, current_character, engine, guild=guild)
                            and not first_pass
                    ):
                        logging.info("BAI15: Integrity check failed")
                        # print(f"integrity check was false: init_pos: {init_pos}")
                        for pos, row in enumerate(init_list):
                            await asyncio.sleep(0)
                            if row.name == current_character:
                                init_pos = pos
                                # print(f"integrity checked init_pos: {init_pos}")
                    init_pos += 1  # increase the init position by 1
                    # print(f"new init_pos: {init_pos}")
                    if init_pos >= len(init_list):  # if it has reached the end, loop back to the beginning
                        init_pos = 0
                        guild.round += 1
                        if guild.timekeeping:  # if timekeeping is enable on the server
                            # Advance time time by the number of seconds in the guild.time column. Default is 6
                            # seconds ala D&D standard
                            await advance_time(ctx, engine, bot, second=guild.time, guild=guild)
                            await check_cc(ctx, engine, bot, guild=guild)
                            logging.info("BAI16: cc checked")

                            # block initiative loop
                # check to see if the next character is player vs npc
                # print(init_list)
                # print(f"init_pos: {init_pos}, len(init_list): {len(init_list)}")
                if init_pos >= len(init_list) - 1:
                    # print(f"init_pos: {init_pos}")
                    if init_list[init_pos].player != init_list[0].player:
                        block_done = True
                elif init_list[init_pos].player != init_list[init_pos + 1].player:
                    block_done = True
                if not guild.block:
                    block_done = True

                turn_list.append(init_list[init_pos].name)
                current_character = init_list[init_pos].name
                iterations += 1
                if iterations >= len(init_list):  # stop an infinite loop
                    block_done = True

                # print(turn_list)

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
                logging.info(f"BAI17: guild updated: {guild.id}")
                # Out side while statement - for reference
                guild.initiative = init_pos  # set it
                # print(f"final init_pos: {init_pos}")
                guild.saved_order = str(init_list[init_pos].name)
                logging.info(f"BAI18: saved order: {guild.saved_order}")
                await session.commit()
                logging.info("BAI19: Writted")
            await engine.dispose()
            return True
        except Exception as e:
            logging.error(f"block_advance_initiative: {e}")
            if ctx is not None:
                report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
                await report.report()