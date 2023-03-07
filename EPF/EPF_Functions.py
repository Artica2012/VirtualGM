import asyncio
import logging
import os

# imports

import discord
from dotenv import load_dotenv
from sqlalchemy import true
from sqlalchemy.exc import NoResultFound
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import d20

from PF2e.pf2_functions import PF2_eval_succss
from EPF.EPF_Character import get_EPF_Character
from utils.utils import get_guild
from database_models import (
    get_condition,
)
from error_handling_reporting import ErrorReport, error_not_initialized
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



