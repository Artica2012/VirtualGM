# pf2_functions.py


import asyncio
import logging
import os

# imports
from datetime import datetime

import discord
from discord import Interaction
from dotenv import load_dotenv
from sqlalchemy import or_, select, false, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import d20

from Generic.Tracker import get_init_list
from utils.utils import get_guild
from utils.Char_Getter import get_character
import Generic.character_functions

from database_models import Global, get_condition, get_tracker
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, get_time
from utils.parsing import ParseModifiers
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA

D4e_attributes = ["AC", "Fort", "Reflex", "Will"]
D4e_base_roll = d20.roll(f"{10}")


# Attack function specific for PF2
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
    roll_list = roll.split(":")
    if len(roll_list) == 1:
        roll = roll
    else:
        roll = roll_list[1]

    # Roll the dice
    # print(roll)
    try:
        roll_string: str = f"{roll}{ParseModifiers(attack_modifier)}"
    except:
        roll_string = roll
    dice_result = d20.roll(roll_string)
    # print(dice_result)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    guild = await get_guild(ctx, None)
    Tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)

    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker.id).where(Tracker.name == target))
            targ = result.scalars().one()

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"attack: {e}")
        report = ErrorReport(ctx, "/attack (emp)", e, bot)
        await report.report()
        return False

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == targ).where(Condition.title == vs)
            )
            con_vs = result.scalars().one()
    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"get_cc: {e}")
        report = ErrorReport(ctx, "/attack (con)", e, bot)
        await report.report()
        return False

    logging.info(f"Target Modifier: {target_modifier}")

    try:
        target_string = f"{con_vs.number}{ParseModifiers(target_modifier)}"
        goal = d20.roll(target_string)
    except Exception as e:
        report = ErrorReport(ctx, "/attack (con)", e, bot)
        await report.report()
        return False

    # Result processing
    success_string = D4e_eval_success(dice_result, goal)
    output_string = f"{character} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
    return output_string


async def save(ctx: discord.ApplicationContext, engine, bot, character: str, condition: str, modifier: str, guild=None):
    guild = await get_guild(ctx, guild)
    Character_Model = await get_character(character, guild=guild, engine=engine)

    try:
        roll_string = f"1d20{ParseModifiers(modifier)}"
        dice_result = d20.roll(roll_string)
        success_string = D4e_eval_success(dice_result, D4e_base_roll)
        # Format output string
        output_string = f"Save: {character}\n{dice_result}\n{success_string}"
        # CC modify
        if dice_result.total >= D4e_base_roll.total:
            await Character_Model.delete_cc(condition)

        return output_string

    except NoResultFound:
        if ctx is not None:
            await ctx.channel.send(error_not_initialized, delete_after=30)
        return "Error"
    except Exception as e:
        logging.warning(f"save: {e}")
        if ctx is not None:
            report = ErrorReport(ctx, "/d4e save", e, bot)
            await report.report()
        return "Error"


def D4e_eval_success(dice_result: d20.RollResult, goal: d20.RollResult):
    success_string = ""
    match dice_result.crit:
        case d20.CritType.CRIT:
            success_string = "Success"
        case d20.CritType.FAIL:
            success_string = "Failure"
        case _:
            success_string = "Success" if dice_result.total >= goal.total else "Failure"

    return success_string


# Builds the tracker string. Updated to work with block initiative



class D4eConditionButton(discord.ui.Button):
    def __init__(self, condition, ctx: discord.ApplicationContext, bot, character, guild=None):
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

        self.bot = bot
        self.character = character
        self.condition = condition
        self.guild = guild
        super().__init__(
            label=condition.title,
            style=discord.ButtonStyle.primary,
            custom_id=str(f"{condition.character_id}_{condition.title}"),
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Saving...")
        self.guild = await initiative.get_guild(self.ctx, self.guild)
        if interaction.user.id == self.character.user or gm_check(self.ctx, self.engine, self.guild):
            try:

                output_string = await save(
                    self.ctx, self.engine, self.bot, self.character.name, self.condition.title, modifier="",
                    guild=self.guild
                )
                await interaction.edit_original_response(content=output_string)
                await initiative.update_pinned_tracker(
                    self.ctx, self.engine, self.bot, guild=self.guild
                )
            except Exception:
                output_string = "Unable to process save, perhaps the condition was removed."
                await interaction.edit_original_response(content=output_string)
        else:
            output_string = "Roll your own save!"
            await interaction.edit_original_response(content=output_string)

        # await self.ctx.channel.send(output_string)


# Checks to see if the user of the slash command is the GM, returns a boolean
async def gm_check(ctx, engine, guild=None):
    if ctx is None and guild is None:
        raise LookupError("No guild reference")

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
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

            if int(guild.gm) != int(ctx.interaction.user.id):
                return False
            else:
                return True
    except Exception:
        return False


async def D4eTrackerButtons(ctx: discord.ApplicationContext, bot, guild=None):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    guild = await initiative.get_guild(ctx, guild, refresh=True)
    Tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    view = discord.ui.View(timeout=None)


    init_list = await get_init_list(ctx, engine, guild=guild)

    async with async_session() as session:
        result = await session.execute(select(Tracker).where(Tracker.name == init_list[guild.initiative].name))
        char = result.scalars().one()

    async with async_session() as session:
        result = await session.execute(
            select(Condition).where(Condition.character_id == char.id).where(Condition.flex == true())
        )
        conditions = result.scalars().all()
    for con in conditions:
        new_button = D4eConditionButton(con, ctx, bot, char, guild=guild)
        view.add_item(new_button)
    return view
