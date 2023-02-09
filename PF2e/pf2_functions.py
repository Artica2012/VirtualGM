# pf2_functions.py
import logging
import os

# imports
from datetime import datetime

import discord
import asyncio
import sqlalchemy as db
from discord import option, Interaction
from discord.commands import SlashCommandGroup, option
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

import database_models
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
PF2_saves = ['Fort', 'Reflex', 'Will']


async def attack(ctx: discord.ApplicationContext, engine, bot, character: str, target: str, roll: str, vs: str,
                 attack_modifier: str, target_modifier: str):
    roller = DiceRoller('')
    # try:

    # Strip a macro:
    roll_list = roll.split(':')
    print(roll_list)
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

    logging.info(f"Target Modifier: {target_modifier}")

    if target_modifier != '':

        if target_modifier[0] == '-' or target_modifier[0] == '+':
            target_modifier_string = target_modifier
        else:
            target_modifier_string = f"+{target_modifier}"

        try:
            target_modifier = int(target_modifier)
            goal = goal_value + int(target_modifier)

        except:
            if target_modifier[0] == '+':
                goal = goal_value + int(target_modifier[1:])
            elif target_modifier[0] == '-':
                goal = goal_value - int(target_modifier[1:])
            else:
                goal = goal_value
    else:
        goal = goal_value
    logging.info(f"Goal: {goal}")

    success_string = await PF2_eval_succss(dice_result, goal)

    # print(f"{dice_string}, {total}\n"
    #       f"{vs}, {goal_value}\n {success_string}")
    # Format output string
    if target_modifier != '':
        output_string = f"{character} vs {target} {vs} {target_modifier_string}:\n" \
                        f"{dice_string} = {total}\n" \
                        f"{success_string}"
    else:
        output_string = f"{character} vs {target} {vs}:\n" \
                        f"{dice_string} = {total}\n" \
                        f"{success_string}"
    return output_string


async def save(ctx: discord.ApplicationContext, engine, bot, character: str, target: str, vs: str, dc:int,  modifier: str):
    if target == None:
        output_string = "Error. No Target Specified."
        return output_string
    roller = DiceRoller('')

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    Tracker = await get_tracker(ctx, engine)
    Condition = await get_condition(ctx, engine)
    orig_dc = dc
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

        if dc == None:
            async with async_session() as session:
                result = await session.execute(select(Condition.number).where(Condition.character_id == char.id)
                                               .where(Condition.title == 'DC'))
                dc = result.scalars().one()


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
        if character == target:
            if orig_dc == None:
                output_string = f"{character} makes a {vs} save!\n" \
                                f"{dice_string} = {total}\n"

            else:
                output_string = f"{character} makes a {vs} save!\n" \
                                f"{dice_string} = {total}\n" \
                                f"{success_string}"

        else:
            output_string = f"{target} makes a {vs} save!\n" \
                            f"{character} forced the save.\n" \
                            f"{dice_string} = {total}\n" \
                            f"{success_string}"

            # output_string = f"{character} vs {target}\n" \
            #                 f" {vs} Save\n" \
            #                 f"{dice_string} = {total}\n" \
            #                 f"{success_string}"

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
                          gm: bool = False, guild=None):
    print("PF2 Get Tracker")
    # Get the datetime
    datetime_string = ''
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    async with async_session() as session:
        if ctx == None:
            result = await session.execute(select(Global).where(
                Global.id == guild.id))
        else:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )))
        guild = result.scalars().one()
        logging.info(f"BGT1: Guild: {guild.id}")
        if guild.block and guild.initiative != None:
            turn_list = await initiative.get_turn_list(ctx, engine, bot, guild=guild)
            block = True
        else:
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
            datetime_string = f" {await output_datetime(ctx, engine, bot, guild=guild)}\n" \
                              f"________________________\n"
    except NoResultFound as e:
        if ctx != None:
            await ctx.channel.send(
                error_not_initialized,
                delete_after=30)
        logging.info("Channel Not Set Up")
    except Exception as e:
        logging.error(f'get_tracker: {e}')
        report = ErrorReport(ctx, "get_tracker", e, bot)
        await report.report()

    try:
        Condition = await get_condition(ctx, engine, id=guild.id)

        if guild.round != 0:
            round_string = f"Round: {guild.round}"
        else:
            round_string = ""

        output_string = f"```{datetime_string}" \
                        f"Initiative: {round_string}\n"

        for x, row in enumerate(init_list):
            logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
            if len(init_list) > active_length and x == active_length:
                output_string += '-----------------\n' # Put in the divider
            async with async_session() as session:
                result = await session.execute(select(Condition)
                                               .where(Condition.character_id == row.id)
                                               .where(Condition.visible == True))
                condition_list = result.scalars().all()
            try:
                async with async_session() as session:
                    result = await session.execute(select(Condition)
                                                   .where(Condition.character_id == row.id)
                                                   .where(Condition.visible == False)
                                                   .where(Condition.title == 'AC'))
                    armor_class = result.scalars().one()
                    # print(armor_class.number)
                    ac = armor_class.number
            except Exception as e:
                ac = ""

            await asyncio.sleep(0)
            sel_bool = False
            selector = ''

            # don't show an init if not in combat
            if row.init == 0:
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
                selector = '>>'
            if row.player or gm:
                if row.temp_hp != 0:
                    string = f"{selector}  {init_string} {str(row.name).title()}: {row.current_hp}/{row.max_hp} ({row.temp_hp}) Temp AC:{ac}\n"
                else:
                    string = f"{selector}  {init_string} {str(row.name).title()}: {row.current_hp}/{row.max_hp} AC: {ac}\n"
            else:
                hp_string = await initiative.calculate_hp(row.current_hp, row.max_hp)
                string = f"{selector}  {init_string} {str(row.name).title()}: {hp_string} \n"
            output_string += string

            for con_row in condition_list:
                logging.info(f"BGT5: con_row in row[cc] {con_row.title} {con_row.id}")
                # print(con_row)
                await asyncio.sleep(0)
                if gm or not con_row.counter:
                    if con_row.number != None and con_row.number > 0:
                        if con_row.time:
                            time_stamp = datetime.fromtimestamp(con_row.number)
                            current_time = await get_time(ctx, engine, bot, guild=guild)
                            time_left = time_stamp - current_time
                            days_left = time_left.days
                            processed_minutes_left = divmod(time_left.seconds, 60)[0]
                            processed_seconds_left = divmod(time_left.seconds, 60)[1]
                            if processed_seconds_left < 10:
                                processed_seconds_left = f"0{processed_seconds_left}"
                            if days_left != 0:
                                con_string = f"       {con_row.title}: {days_left} Days, {processed_minutes_left}:{processed_seconds_left}\n "
                            else:
                                con_string = f"       {con_row.title}: {processed_minutes_left}:{processed_seconds_left}\n"
                        else:
                            con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = f"       {con_row.title}\n"

                elif con_row.counter == True and sel_bool and row.player:
                    if con_row.number != 0:
                        con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = f"       {con_row.title}\n"
                else:
                    con_string = ''
                output_string += con_string
                # print(output_string)
        output_string += f"```"
        # print(output_string)
        await engine.dispose()
        return output_string
    except Exception as e:
        logging.info(f"block_get_tracker: {e}")
        if ctx !=  None:
            report = ErrorReport(ctx, pf2_get_tracker.__name__, e, bot)
            await report.report()


async def edit_stats(ctx, engine, bot, name: str):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == name))
            character = result.scalars().one()

        Condition = await get_condition(ctx, engine, id=guild.id)
        async with async_session() as session:
            result = await session.execute(select(Condition).where(Condition.character_id == character.id))
            conditions = result.scalars().all()
        condition_dict = {}
        for con in conditions:
            await asyncio.sleep(0)
            condition_dict[con.title] = con.number
        editModal = PF2EditCharacterModal(character=character, cons=condition_dict, ctx=ctx, engine=engine, bot=bot,
                                          title=character.name)
        await ctx.send_modal(editModal)

        return True

    except Exception as e:
        return False


class PF2EditCharacterModal(discord.ui.Modal):
    def __init__(self, character, cons: dict, ctx: discord.ApplicationContext, engine, bot, *args, **kwargs):
        self.character = character,
        self.cons = cons,
        self.name = character.name
        self.player = ctx.user.id
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        super().__init__(
            discord.ui.InputText(
                label="AC",
                placeholder="Armor Class",
                value=cons['AC']
            ),
            discord.ui.InputText(
                label="Fort",
                placeholder="Fortitude",
                value=cons['Fort']
            ),
            discord.ui.InputText(
                label="Reflex",
                placeholder="Reflex",
                value=cons['Reflex']
            ),
            discord.ui.InputText(
                label="Will",
                placeholder="Will",
                value=cons['Will']
            ),
            discord.ui.InputText(
                label="DC",
                placeholder="DC",
                value=cons['DC']
            ), *args, **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_message(f'{self.name} Updated')
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == self.ctx.interaction.channel_id,
                    Global.gm_tracker_channel == self.ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

        embed = discord.Embed(
            title="Character Updated (PF2)",
            fields=[
                discord.EmbedField(
                    name="Name: ", value=self.name, inline=True
                ),
                discord.EmbedField(
                    name="AC: ", value=self.children[0].value, inline=True
                ),
                discord.EmbedField(
                    name="Fort: ", value=self.children[1].value, inline=True
                ),
                discord.EmbedField(
                    name="Reflex: ", value=self.children[2].value, inline=True
                ),
                discord.EmbedField(
                    name="Will: ", value=self.children[3].value, inline=True
                ),
                discord.EmbedField(
                    name="Class/Spell DC: ", value=self.children[4].value, inline=True
                ),
            ],
            color=discord.Color.dark_gold(),
        )

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(self.ctx, self.engine, id=guild.id)

        Condition = await get_condition(self.ctx, self.engine, id=guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
            character = char_result.scalars().one()

        for item in self.children:
            async with async_session() as session:
                result = await session.execute(select(Condition)
                                               .where(Condition.character_id == character.id)
                                               .where(Condition.title == item.label))
                condition = result.scalars().one()
                condition.number = int(item.value)
                await session.commit()

        await initiative.update_pinned_tracker(self.ctx, self.engine, self.bot)
        # print('Tracker Updated')

        await self.ctx.channel.send(embeds= await initiative.get_char_sheet(self.ctx, self.engine, self.bot, self.name))

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        print(error)
        self.stop()



