# pf2_functions.py


import os

# imports
from datetime import datetime

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

import initiative
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
                 attack_modifier: str, target_modifier: str):
    roller = DiceRoller('')
    # try:

    # Strip a macro:
    roll_list = roll.split(':')
    if len(roll_list) == 1:
        roll = roll
    else:
        roll = roll_list[1]

    if attack_modifier != '':
        if attack_modifier[0] == '+' or attack_modifier[0] == '-':
            roll_string = roll + attack_modifier
        else:
            roll_string = roll + '+' + attack_modifier
    else:
        roll_string = roll
    print(roll_string)
    dice_result = await roller.attack_roll(roll_string)
    total = dice_result[1]
    dice_string = dice_result[0]
    # return
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


async def save(ctx: discord.ApplicationContext, engine, bot, character: str, target: str, vs: str, modifier: str):
    if target == None:
        output_string = "Error. No Target Specified."
        return output_string
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


# Builds the tracker string. Updated to work with block initiative
async def pf2_get_tracker(init_list: list, selected: int, ctx: discord.ApplicationContext, engine, bot,
                          gm: bool = False):
    # Get the datetime
    datetime_string = ''
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(Global).where(
            or_(
                Global.tracker_channel == ctx.interaction.channel_id,
                Global.gm_tracker_channel == ctx.interaction.channel_id
            )
        )
        )
        guild = result.scalars().one()
        if guild.block and guild.initiative != None:
            turn_list = await initiative.get_turn_list(ctx, engine, bot)
            block = True
        else:
            block = False
        round = guild.round
    try:
        if await check_timekeeper(ctx, engine):
            datetime_string = f" {await output_datetime(ctx, engine, bot)}\n" \
                              f"________________________\n"
    except NoResultFound as e:
        await ctx.channel.send(
            error_not_initialized,
            delete_after=30)
    except Exception as e:
        print(f'get_tracker: {e}')
        report = ErrorReport(ctx, "get_tracker", e, bot)
        await report.report()

    try:
        Condition = await get_condition(ctx, engine, id=guild.id)
        row_data = []
        for row in init_list:
            async with async_session() as session:
                result = await session.execute(select(Condition).where(Condition.character_id == row.id))
                con = result.scalars().all()
            row_data.append({'id': row.id,
                             'name': row.name,
                             'init': row.init,
                             'player': row.player,
                             'user': row.user,
                             'chp': row.current_hp,
                             'maxhp': row.max_hp,
                             'thp': row.temp_hp,
                             'cc': con
                             })

        if round != 0:
            round_string = f"Round: {round}"
        else:
            round_string = ""

        output_string = f"```{datetime_string}" \
                        f"Initiative: {round_string}\n"
        for x, row in enumerate(row_data):
            await asyncio.sleep(0)
            sel_bool = False
            selector = ''

            # don't show an init if not in combat
            if row['init'] == 0:
                init_string = ""
            else:
                init_string = f"{row['init']}"

            if block:
                for character in turn_list:
                    if row['id'] == character.id:
                        sel_bool = True
            else:
                if x == selected:
                    sel_bool = True

            # print(f"{row['name']}: x: {x}, selected: {selected}")

            if sel_bool:
                selector = '>>'
            if row['player'] or gm:
                if row['thp'] != 0:
                    string = f"{selector}  {init_string} {str(row['name']).title()}: {row['chp']}/{row['maxhp']} ({row['thp']}) Temp\n"
                else:
                    string = f"{selector}  {init_string} {str(row['name']).title()}: {row['chp']}/{row['maxhp']}\n"
            else:
                hp_string = await initiative.calculate_hp(row['chp'], row['maxhp'])
                string = f"{selector}  {init_string} {str(row['name']).title()}: {hp_string} \n"
            output_string += string

            for con_row in row['cc']:
                # print(f"{con_row.number}, {con_row.character_id}")
                await asyncio.sleep(0)
                if con_row.visible == True:
                    if gm or not con_row.counter:
                        if con_row.number != None and con_row.number > 0:
                            if con_row.time:
                                time_stamp = datetime.fromtimestamp(con_row.number)
                                current_time = await get_time(ctx, engine, bot)
                                time_left = time_stamp - current_time
                                days_left = time_left.days
                                processed_minutes_left = divmod(time_left.seconds, 60)[0]
                                processed_seconds_left = divmod(time_left.seconds, 60)[1]
                                if processed_seconds_left < 10:
                                    processed_seconds_left = f"0{processed_seconds_left}"
                                if days_left != 0:
                                    con_string = f"       {con_row.title}: {days_left} Days, {processed_minutes_left}:{processed_seconds_left}\n"
                                else:
                                    con_string = f"       {con_row.title}: {processed_minutes_left}:{processed_seconds_left}\n"
                            else:
                                con_string = f"       {con_row.title}: {con_row.number}\n"
                        else:
                            con_string = f"       {con_row.title}\n"

                    elif con_row.counter == True and sel_bool and row['player']:
                        con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = ''
                    output_string += con_string
                else:
                    if con_row.title == 'AC' and row['player'] == True:
                        con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = ''
                    output_string += con_string
        output_string += f"```"
        # print(output_string)
        await engine.dispose()
        return output_string
    except Exception as e:
        print(f"pf2_get_tracker: {e}")
        report = ErrorReport(ctx, pf2_get_tracker.__name__, e, bot)
        await report.report()
