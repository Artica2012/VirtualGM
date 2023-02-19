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
import initiative
from database_models import Global, get_condition, get_tracker
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, get_time
from utils.parsing import ParseModifiers

# define global variables

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")

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
    guild = await initiative.get_guild(ctx, None)
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
        print(f"attack: {e}")
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
        print(f"get_cc: {e}")
        report = ErrorReport(ctx, "/attack (con)", e, bot)
        await report.report()
        return False

    logging.info(f"Target Modifier: {target_modifier}")

    try:
        print(con_vs.number)
        print(ParseModifiers(target_modifier))
        target_string = f"{con_vs.number}{ParseModifiers(target_modifier)}"
        print(target_string)
        goal = d20.roll(target_string)
    except Exception as e:
        report = ErrorReport(ctx, "/attack (con)", e, bot)
        await report.report()
        return False

    # Result processing
    success_string = D4e_eval_success(dice_result, goal)
    output_string = f"{character} vs {target} {vs} {target_string}:\n{dice_result}\n{success_string}"
    return output_string


async def save(ctx: discord.ApplicationContext, engine, bot, character: str, condition: str, modifier: str):
    try:
        roll_string = f"1d20{ParseModifiers(modifier)}"
        dice_result = d20.roll(roll_string)
        success_string = D4e_eval_success(dice_result, D4e_base_roll)
        # Format output string
        output_string = f"Save: {character}\n{dice_result}\n{success_string}"
        # CC modify
        if dice_result.total >= D4e_base_roll.total:
            await initiative.delete_cc(ctx, engine, character, condition, bot)

        return output_string

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return "Error"
    except Exception as e:
        print(f"attack: {e}")
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
async def d4e_get_tracker(
    init_list: list, selected: int, ctx: discord.ApplicationContext, engine, bot, gm: bool = False, guild=None
):
    # Get the datetime
    datetime_string = ""
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    if ctx is None and guild is None:
        raise LookupError("No guild reference")

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
        if guild.block and guild.initiative is not None:
            turn_list = await initiative.get_turn_list(ctx, engine, bot)
            block = True
        else:
            block = False
        round = guild.round

    # Code for appending the inactive list onto the init_list
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
    except Exception as e:
        print(f"get_tracker: {e}")
        report = ErrorReport(ctx, "get_tracker", e, bot)
        await report.report()

    try:
        Condition = await get_condition(ctx, engine, id=guild.id)

        if round != 0:
            round_string = f"Round: {round}"
        else:
            round_string = ""

        output_string = f"```{datetime_string}Initiative: {round_string}\n"

        for x, row in enumerate(init_list):
            logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
            if len(init_list) > active_length and x == active_length:
                output_string += "-----------------\n"  # Put in the divider
            # print(f'row.id= {row.id}')
            async with async_session() as session:
                result = await session.execute(
                    select(Condition).where(Condition.character_id == row.id).where(Condition.visible == true())
                )
                condition_list = result.scalars().all()

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
                        f" {row.current_hp}/{row.max_hp} ({row.temp_hp}) Temp\n"
                    )
                else:
                    string = f"{selector}  {init_string} {str(row.name).title()}: {row.current_hp}/{row.max_hp}\n"
            else:
                hp_string = await initiative.calculate_hp(row.current_hp, row.max_hp)
                string = f"{selector}  {init_string} {str(row.name).title()}: {hp_string} \n"
            output_string += string

            for con_row in condition_list:
                await asyncio.sleep(0)
                if con_row.visible is True:
                    if gm or not con_row.counter:
                        if con_row.number is not None and con_row.number > 0:
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
                                    con_string = (
                                        f"       {con_row.title}: {days_left} Days,"
                                        f" {processed_minutes_left}:{processed_seconds_left}\n"
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
                        con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = ""
                    output_string += con_string
                else:
                    con_string = ""
                    output_string += con_string
        output_string += "```"
        # print(output_string)
        await engine.dispose()
        return output_string
    except Exception as e:
        if ctx is not None:
            report = ErrorReport(ctx, d4e_get_tracker.__name__, e, bot)
            await report.report()
        logging.info(f"d4e_get_tracker: {e}")


async def d4e_condition_buttons():
    pass


class D4eConditionButton(discord.ui.Button):
    def __init__(self, condition, ctx: discord.ApplicationContext, engine, bot, character, guild=None):
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
        if interaction.user.id == self.character.user or gm_check(self.ctx, self.engine, self.guild):
            try:
                if self.ctx is not None:
                    output_string = await save(
                        self.ctx, self.engine, self.bot, self.character.name, self.condition.title, modifier=""
                    )
                else:
                    output_string = await saveIndependent(
                        self.engine, self.bot, self.guild, self.character.name, self.condition.title, modifier=""
                    )
                await interaction.edit_original_message(content=output_string)
                # await interaction.response.send_message(
                #     await save(
                #       self.ctx,
                #       self.engine,
                #       self.bot,
                #       self.character.name,
                #       self.condition.title,
                #       modifier=""
                #     )
                # )
                await initiative.block_update_init(
                    self.ctx, interaction.message.id, self.engine, self.bot, guild=self.guild
                )
            except Exception:
                output_string = "Unable to process save, perhaps the condition was removed."
                await interaction.edit_original_message(content=output_string)
        else:
            output_string = "Roll your own save!"
            await interaction.edit_original_message(content=output_string)

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


async def edit_stats(ctx, engine, bot, name: str):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id,
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
        editModal = D4eEditCharacterModal(
            character=character, cons=condition_dict, ctx=ctx, engine=engine, bot=bot, title=character.name
        )
        await ctx.send_modal(editModal)

        return True

    except Exception:
        return False


# D&D 4e Specific
class D4eEditCharacterModal(discord.ui.Modal):
    def __init__(self, character, cons: dict, ctx: discord.ApplicationContext, engine, bot, *args, **kwargs):
        self.character = character
        self.cons = (cons,)
        self.name = character.name
        self.player = ctx.user.id
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        super().__init__(
            discord.ui.InputText(label="AC", placeholder="Armor Class", value=cons["AC"]),
            discord.ui.InputText(label="Fort", placeholder="Fortitude", value=cons["Fort"]),
            discord.ui.InputText(label="Reflex", placeholder="Reflex", value=cons["Reflex"]),
            discord.ui.InputText(label="Will", placeholder="Will", value=cons["Will"]),
            *args,
            **kwargs,
        )

    async def callback(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_message(f"{self.name} Updated")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(
                select(Global).where(
                    or_(
                        Global.tracker_channel == self.ctx.interaction.channel_id,
                        Global.gm_tracker_channel == self.ctx.interaction.channel_id,
                    )
                )
            )
            guild = result.scalars().one()

        discord.Embed(
            title="Character Updated (D&D 4e)",
            fields=[
                discord.EmbedField(name="Name: ", value=self.name, inline=True),
                discord.EmbedField(name="AC: ", value=self.children[0].value, inline=True),
                discord.EmbedField(name="Fort: ", value=self.children[1].value, inline=True),
                discord.EmbedField(name="Reflex: ", value=self.children[2].value, inline=True),
                discord.EmbedField(name="Will: ", value=self.children[3].value, inline=True),
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
                result = await session.execute(
                    select(Condition).where(Condition.character_id == character.id).where(Condition.title == item.label)
                )
                condition = result.scalars().one()
                condition.number = int(item.value)
                await session.commit()

        await initiative.update_pinned_tracker(self.ctx, self.engine, self.bot)
        # print('Tracker Updated')
        await self.ctx.channel.send(embeds=await initiative.get_char_sheet(self.ctx, self.engine, self.bot, self.name))

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        print(error)
        self.stop()


async def D4eTrackerButtons(ctx: discord.ApplicationContext, bot, guild, init_list):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    Tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    view = discord.ui.View(timeout=None)
    print("Here")
    print(init_list)
    print(guild.initiative)
    async with async_session() as session:
        result = await session.execute(select(Tracker).where(Tracker.name == init_list[guild.initiative].name))
        char = result.scalars().one()
        print(char)
    async with async_session() as session:
        result = await session.execute(
            select(Condition).where(Condition.character_id == char.id).where(Condition.flex == true())
        )
        conditions = result.scalars().all()
    for con in conditions:
        new_button = D4eConditionButton(con, ctx, engine, bot, char, guild=guild)
        view.add_item(new_button)
    return view


async def D4eTrackerButtonsIndependent(bot, guild):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tracker = await get_tracker(None, engine, id=guild.id)
    condition = await get_condition(None, engine, id=guild.id)

    async with async_session() as session:
        result = await session.execute(select(tracker).order_by(tracker.init.desc()).order_by(tracker.id.desc()))
        init_list = result.scalars().all()
    await engine.dispose()

    view = discord.ui.View(timeout=None)
    async with async_session() as session:
        result = await session.execute(select(tracker).where(tracker.name == init_list[guild.initiative].name))
        char = result.scalars().one()
    async with async_session() as session:
        result = await session.execute(
            select(condition)
            .where(condition.character_id == char.id)
            .where(condition.counter == false())
            .where(condition.flex == true())
        )
        conditions = result.scalars().all()
    for con in conditions:
        new_button = D4eConditionButtonIndependent(con, bot, char, guild)
        view.add_item(new_button)
    return view


class D4eConditionButtonIndependent(discord.ui.Button):
    def __init__(self, condition, bot, character, guild):
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        self.guild = guild
        self.character = character
        self.condition = condition
        super().__init__(
            label=condition.title,
            style=discord.ButtonStyle.primary,
            custom_id=str(f"{condition.character_id}_{condition.title}"),
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Saving...")

        if int(self.guild.gm) != int(interaction.user.id):
            gm = False
        else:
            gm = True

        if interaction.user.id == self.character.user or gm:
            # try:
            output_string = await saveIndependent(
                self.engine, self.bot, self.guild, self.character.name, self.condition.title, modifier=""
            )
            # print(output_string)
            await interaction.edit_original_message(content=output_string)
            print(interaction.message.id)
            await initiative.block_update_init(None, interaction.message.id, self.engine, self.bot, guild=self.guild)
            # except Exception:
            #     output_string = 'Unable to process save, perhaps the condition was removed.'
            #     await interaction.edit_original_message(content=output_string)
        else:
            output_string = "Roll your own save!"
            await interaction.edit_original_message(content=output_string)

        # await self.ctx.channel.send(output_string)


async def saveIndependent(engine, bot, guild, character: str, condition: str, modifier: str):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    roll_string = f"1d20{ParseModifiers(modifier)}"
    dice_result = d20.roll(roll_string)

    success_string = D4e_eval_success(dice_result, D4e_base_roll)
    # Format output string
    output_string = f"Save: {character}\n{dice_result}\n{success_string}"

    if dice_result.total >= D4e_base_roll.total:
        try:
            Tracker = await get_tracker(None, engine, id=guild.id)
            Condition = await get_condition(None, engine, id=guild.id)

            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == character))
                character = result.scalars().one()

        except NoResultFound:
            logging.info("Error")
        except Exception as e:
            logging.info(f"delete_cc: {e}")

        async with async_session() as session:
            result = await session.execute(
                select(Condition)
                .where(Condition.character_id == character.id)
                .where(Condition.visible == true())
                .where(Condition.title == condition)
            )
            con_list = result.scalars().all()
        if len(con_list) == 0:
            await engine.dispose()
            return False

        for con in con_list:
            await asyncio.sleep(0)
            async with async_session() as session:
                await session.delete(con)
                await session.commit()

        await initiative.update_pinned_tracker(None, engine, bot, guild=guild)
        await engine.dispose()

    return output_string
