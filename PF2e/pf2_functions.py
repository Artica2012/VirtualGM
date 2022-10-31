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
    get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time
from PF2e.pathbuilder_importer import pathbuilder_import

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


async def attack(ctx: discord.ApplicationContext, engine, bot, character: str, target: str, roll: str, vs: str):
    roller = DiceRoller('')
    metadata = db.MetaData()
    try:
        dice_result = await roller.attack_roll(roll)
        total = dice_result[1]
        dice_string = dice_result[0]
    except Exception as e:
        await ctx.send_followup('Error in the dice string. Check Syntax')
        return

    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        con = await get_condition_table(ctx, metadata, engine)
        emp_stmt = emp.select().where(emp.c.name == character)
        async with engine.begin() as conn:
            data = []
            for row in await conn.execute(emp_stmt):
                data.append(row)
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
        con_stmt = con.select().where(con.c.character_id == data[0][0]).where(con.c.title == vs)
        con_data = []
        async with engine.begin() as conn:
            for row in await conn.execute(con_stmt):
                con_data.append(row)
        await engine.dispose()
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'get_cc: {e}')
        report = ErrorReport(ctx, "/attack (con)", e, bot)
        await report.report()
        return False

    goal_value = con_data[0][4]
    success_string = await PF2_eval_succss(dice_result, goal_value)
    # Format output string
    output_string = f"{character} vs {target} {vs}:\n" \
                    f"{dice_string} = {total}\n" \
                    f"{success_string}"
    return output_string

async def save(ctx: discord.ApplicationContext, engine, bot, character: str, target: str, vs: str):
    roller = DiceRoller('')
    metadata = db.MetaData()
    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        con = await get_condition_table(ctx, metadata, engine)

        char_sel_stmt = emp.select().where(emp.c.name == character)
        target_sel_stmt = emp.select().where(emp.c.name == target)
        async with engine.begin() as conn:
            charID = None
            targetID = None
            roll = ''
            dc = None
            for row in await conn.execute(char_sel_stmt):
                charID = row[0]
            for row in await conn.execute(target_sel_stmt):
                targetID = row[0]

            roll_stmt = con.select().where(con.c.character_id == targetID).where(con.c.title == vs)
            dc_stmt = con.select().where(con.c.character_id == charID).where(con.c.title == 'DC')
            for row in await conn.execute(roll_stmt):
                roll = f"1d20+{row[4]}"
            for row in await conn.execute(dc_stmt):
                dc = row[4]

        dice_result = await roller.attack_roll(roll)
        total = dice_result[1]
        dice_string = dice_result[0]

        success_string = await PF2_eval_succss(dice_result, dc)
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


