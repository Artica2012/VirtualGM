import asyncio
import logging
import os

# imports
from datetime import datetime
from math import floor

import aiohttp
import discord
from discord import Interaction
from dotenv import load_dotenv
import sqlalchemy as db
from sqlalchemy import select, false, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, BigInteger
from sqlalchemy import String, Boolean
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

import d20

from PF2e.pf2_functions import PF2_eval_succss
from PF2e.pf2_enhanced_character import get_EPF_Character
from utils.utils import get_guild
from database_models import (
    get_condition,
    get_pf2_e_tracker,
)
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, get_time
from utils.parsing import ParseModifiers

# define global variables

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    # TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    # TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")

PF2_attributes = ["AC", "Fort", "Reflex", "Will", "DC"]
PF2_saves = ["Fort", "Reflex", "Will"]
PF2_base_dc = 10
PF2_skills = ["Acrobatics", "Arcana", "Athletics", "Crafting", "Deception", "Diplomacy", "Intimidation", "Medicine",
              "Nature", "Occultism", "Perception", "Performance", "Religion", "Society", "Stealth", "Survival",
              "Thievery"]


async def attack(
        ctx: discord.ApplicationContext,
        engine,
        bot,
        character: str,
        target: str,
        roll: str,
        vs: str,
        attack_modifier: str,
        target_modifier: str,
):
    # Strip a macro:
    guild = await get_guild(ctx, guild=None)
    try:
        # if type(roll[0]) == int:
        roll_string: str = f"{roll}{ParseModifiers(attack_modifier)}"
        print(roll_string)
        dice_result = d20.roll(roll_string)
        # else:
        #     char_model = await get_EPF_Character(character, ctx, engine=engine)
        #     roll_string = await char_model.get_roll(roll)
        #     print(roll_string)
        #     dice_result = d20.roll(roll_string)
    except:
        char_model = await get_EPF_Character(character, ctx, guild=guild, engine=engine)
        roll_string = f"{await char_model.get_roll(roll)}{ParseModifiers(attack_modifier)}"
        print(roll_string)
        dice_result = d20.roll(roll_string)
    # print(f"{dice_result}")

    # Load up the tables
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    # Throwing guild in here will allow one database query instead of two for getting the tables
    opponent = await get_EPF_Character(target, ctx, guild=guild, engine=engine)
    goal_value = await opponent.get_dc(vs)

    try:
        logging.info(f"Target Modifier: {target_modifier}")
        goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
        logging.info(f"Goal: {goal_string}")
        goal_result = d20.roll(goal_string)
        # print(f"{dice_result}")
    except Exception as e:
        logging.warning(f"attack: {e}")
        report = ErrorReport(ctx, "/a attack (EPF)", e, bot)
        await report.report()
        return False

    # Format output string
    success_string = PF2_eval_succss(dice_result, goal_result)
    output_string = f"{character} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
    return output_string


async def save(
        ctx: discord.ApplicationContext, engine, bot, character: str, target: str, vs: str, dc: int, modifier: str
):
    if target is None:
        output_string = "Error. No Target Specified."
        return output_string
    print(f" {vs}, {dc}, {modifier}")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    guild = await get_guild(ctx, None)
    attacker = await get_EPF_Character(character, ctx, guild=guild, engine=engine)
    opponent = await get_EPF_Character(target, ctx, guild=guild, engine=engine)

    orig_dc = dc

    if dc is None:
        dc = await attacker.get_dc("DC")
        print(dc)
    try:
        print(await opponent.get_roll(vs))
        dice_result = d20.roll(f"{await opponent.get_roll(vs)}{ParseModifiers(modifier)}")
        print(dice_result)
        # goal_string: str = f"{dc}"
        goal_result = d20.roll(f"{dc}")
        print(goal_result)
    except Exception as e:
        logging.warning(f"attack: {e}")
        await ErrorReport(ctx, "/a save (EPF)", e, bot).report()
        return False
    try:
        success_string = PF2_eval_succss(dice_result, goal_result)
        print(success_string)
        # Format output string
        if character == target:
            output_string = f"{character} makes a {vs} save!\n{dice_result}\n{success_string if orig_dc else ''}"
        else:
            output_string = (
                f"{target} makes a {vs} save!\n{character} forced the save.\n{dice_result}\n{success_string}"
            )

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"attack: {e}")
        report = ErrorReport(ctx, "/a save (EPF)", e, bot)
        await report.report()
        return False

    return output_string

# This is the code which check, decrements and removes conditions for the init next turn.
async def EPF_init_con(ctx: discord.ApplicationContext, engine, bot, current_character: str, before: bool, guild=None):
    logging.info(f"{current_character}, {before}")
    logging.info("Decrementing Conditions")

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    guild = await get_guild(ctx, guild)
    character = await get_EPF_Character(current_character, ctx, guild=guild, engine=engine)

    try:
        Condition = await get_condition(ctx, engine, id=guild.id)
        # con = await get_condition_table(ctx, metadata, engine)
        async with async_session() as session:
            if before is not None:
                char_result = await session.execute(
                    select(Condition)
                    .where(Condition.character_id == character.id)
                    .where(Condition.flex == before)
                    .where(Condition.auto_increment == true())
                )
            else:
                char_result = await session.execute(
                    select(Condition)
                    .where(Condition.character_id == character.id)
                    .where(Condition.auto_increment == true())
                )
            con_list = char_result.scalars().all()
            logging.info("BAI9: condition's retrieved")
            # print("First Con List")

        for con_row in con_list:
            logging.info(f"BAI10: con_row: {con_row.title} {con_row.id}")
            await asyncio.sleep(0)
            async with async_session() as session:
                result = await session.execute(select(Condition).where(Condition.id == con_row.id))
                selected_condition = result.scalars().one()
                if not selected_condition.time:  # If auto-increment and NOT time
                    if selected_condition.number >= 2:  # if number >= 2
                        selected_condition.number -= 1
                    else:
                        await session.delete(selected_condition)
                        # await session.commit()
                        logging.info("BAI11: Condition Deleted")
                        if ctx is not None:
                            await ctx.channel.send(f"{con_row.title} removed from {character.name}")
                        else:
                            tracker_channel = bot.get_channel(guild.tracker_channel)
                            await tracker_channel.send(f"{con_row.title} removed from {character.name}")
                    await session.commit()
                elif selected_condition.time:  # If time is true
                    await character.conditions(ctx)

    except Exception as e:
        logging.error(f"block_advance_initiative: {e}")
        if ctx is not None:
            report = ErrorReport(ctx, EPF_init_con.__name__, e, bot)
            await report.report()
