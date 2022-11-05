# pf2_functions.py


import os

# imports
import discord
import asyncio
import sqlalchemy as db
from discord import option
from discord.commands import SlashCommandGroup, option
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from database_models import Global, Base, TrackerTable, ConditionTable, MacroTable, get_tracker_table, \
    get_condition_table, get_macro_table, get_macro, get_condition, get_tracker
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time

# define global variables

load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
    USERNAME = os.getenv('Username')
    PASSWORD = os.getenv('Password')
    HOSTNAME = os.getenv('Hostname')
    PORT = os.getenv('PGPort')
else:
    TOKEN = os.getenv('BETA_TOKEN')
    USERNAME = os.getenv('BETA_Username')
    PASSWORD = os.getenv('BETA_Password')
    HOSTNAME = os.getenv('BETA_Hostname')
    PORT = os.getenv('BETA_PGPort')

GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
DATABASE = os.getenv('DATABASE')

PF2_attributes = ['AC', 'Fort', 'Reflex', 'Will', 'DC']


async def attack(ctx: discord.ApplicationContext, engine, bot, character: str, target: str, roll: str, vs: str,
                 attack_modifier:str, target_modifier:str):
    roller = DiceRoller('')
    try:
        if attack_modifier != '':
            if attack_modifier[0] == '+' or attack_modifier[0] == '-':
                roll_string = roll + attack_modifier
            else:
                roll_string = roll + '+' + attack_modifier
        else:
            roll_string = roll
        dice_result = await roller.attack_roll(roll_string)
        total = dice_result[1]
        dice_string = dice_result[0]
    except Exception as e:
        await ctx.send_followup('Error in the dice string. Check Syntax')
        return
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    Tracker = await get_tracker(ctx, engine)
    Condition = await get_condition(ctx, engine)

    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == target))
            targ = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'attack: {e}')
        report = ErrorReport(ctx, "/attack (emp)", e, bot)
        await report.report()
        return False

    try:
        async with async_session() as session:
            result = await session.execute(select(Condition)
                                           .where(Condition.character_id == targ.id)
                                           .where(Condition.title == vs))
            con_vs = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'get_cc: {e}')
        report = ErrorReport(ctx, "/attack (con)", e, bot)
        await report.report()
        return False

    if vs in ["Fort", "Will", "Reflex"]:
        goal_value = con_vs.number + 10
    else:
        goal_value = con_vs.number
    if target_modifier != '':
        if target_modifier[0] == '+':
            goal = goal_value + int(target_modifier[1:])
        elif target_modifier[0] == '-':
            goal = goal_value - int(target_modifier[1:])
        elif type(target_modifier[0]) == int:
            goal = goal_value + int(target_modifier)
        else:
            goal = goal_value
    else:
        goal = goal_value

    success_string = await PF2_eval_succss(dice_result, goal)

    # print(f"{dice_string}, {total}\n"
    #       f"{vs}, {goal_value}\n {success_string}")
    # Format output string
    output_string = f"{character} vs {target} {vs}:\n" \
                    f"{dice_string} = {total}\n" \
                    f"{success_string}"
    return output_string

async def save(ctx: discord.ApplicationContext, engine, bot, character: str, target: str, vs: str, modifier:str):
    roller = DiceRoller('')

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    Tracker = await get_tracker(ctx, engine)
    Condition = await get_condition(ctx, engine)
    try:

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            char = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == target))
            targ = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(select(Condition).where(Condition.character_id == targ.id)
                                           .where(Condition.title == vs))
            raw_roll = result.scalars().one()
            roll = f"1d20+{raw_roll.number}"

        async with async_session() as session:
            result = await session.execute(select(Condition).where(Condition.character_id == char.id)
                                           .where(Condition.title == 'DC'))
            raw_dc = result.scalars().one()
            dc = raw_dc.number

        if modifier != '':
            if modifier[0] == '+':
                goal = dc + int(modifier[1:])
            elif modifier[0] == '-':
                goal = dc - int(modifier[1:])
            elif type(modifier[0]) == int:
                goal = dc + int(modifier)
            else:
                goal = dc
        else:
            goal = dc
        dice_result = await roller.attack_roll(roll)
        total = dice_result[1]
        dice_string = dice_result[0]

        success_string = await PF2_eval_succss(dice_result, goal)
        # Format output string
        output_string = f"{character} vs {target}\n" \
                        f" {vs} Save\n" \
                        f"{dice_string} = {total}\n" \
                        f"{success_string}"

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'attack: {e}')
        report = ErrorReport(ctx, "/attack (emp)", e, bot)
        await report.report()
        return False

    return output_string


async def PF2_eval_succss(result_tuple: tuple, goal: int):
    total = result_tuple[1]
    nat_twenty = result_tuple[2]
    nat_one = result_tuple[3]
    result = 0
    success_string = ''

    if total >= goal + 10:
        result = 4
    elif total >= goal:
        result = 3
    elif goal >= total >= goal - 9:
        result = 2
    else:
        result = 1

    if nat_twenty:
        result += 1
    elif nat_one:
        result -= 1

    if result >= 4:
        success_string = "Critical Success"
    elif result == 3:
        success_string = "Success"
    elif result == 2:
        success_string = "Failure"
    elif result <= 1:
        success_string = "Critical Failure"
    else:
        success_string = "Error"

    return success_string


