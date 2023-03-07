import logging

import discord
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_tracker, get_condition
from database_operations import get_asyncio_db_engine
from error_handling_reporting import error_not_initialized, ErrorReport
from ui_components import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from utils.Tracker_Getter import get_tracker_model
from utils.utils import get_guild


async def edit_cc_interface(ctx: discord.ApplicationContext, engine, character: str, condition: str, bot, guild=None):
    logging.info("edit_cc_interface")
    view = discord.ui.View()
    try:
        guild = await get_guild(ctx, guild)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker.id).where(Tracker.name == character))
            char = result.scalars().one()
    except NoResultFound:
        if ctx is not None:
            await ctx.channel.send(error_not_initialized, delete_after=30)
        return [None, None]
    except Exception as e:
        logging.info(f"edit_cc: {e}")
        if ctx is not None:
            report = ErrorReport(ctx, edit_cc_interface.__name__, e, bot)
            await report.report()
        return [None, None]
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == char).where(Condition.title == condition)
            )
            cond = result.scalars().one()

            if cond.time or cond.number is None:
                await ctx.send_followup("Unable to edit. Try again in a future update.", ephemeral=True)
                return [None, None]
            else:
                output_string = f"{cond.title}: {cond.number}"
                view.add_item(ConditionMinus(ctx, bot, character, condition, guild))
                view.add_item(ConditionAdd(ctx, bot, character, condition, guild))
                return output_string, view
    except NoResultFound:
        if ctx is not None:
            await ctx.channel.send(error_not_initialized, delete_after=30)
        return [None, None]
    except Exception as e:
        logging.info(f"edit_cc: {e}")
        if ctx is not None:
            report = ErrorReport(ctx, edit_cc_interface.__name__, e, bot)
            await report.report()
        return [None, None]


async def increment_cc(
    ctx: discord.ApplicationContext, engine, character: str, condition: str, add: bool, bot, guild=None
):
    logging.info("increment_cc")
    try:
        guild = await get_guild(ctx, guild)

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker.id).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.info(f"increment_cc: {e}")
        if ctx is not None:
            report = ErrorReport(ctx, increment_cc.__name__, e, bot)
            await report.report()
        return False

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == character).where(Condition.title == condition)
            )
            condition = result.scalars().one()
            current_value = condition.number

            if condition.time or condition.number is None:
                await ctx.send_followup("Unable to edit. Try again in a future update.", ephemeral=True)
                return False
            else:
                if add is True:
                    condition.number = current_value + 1
                else:
                    condition.number = current_value - 1
                await session.commit()
        # await update_pinned_tracker(ctx, engine, bot)
        await engine.dispose()
        return True
    except NoResultFound:
        await ctx.channel.send(error_not_initialized, delete_after=30)
        return False
    except Exception as e:
        logging.warning(f"edit_cc: {e}")
        report = ErrorReport(ctx, "increment_cc", e, bot)
        await report.report()
        return False


class ConditionMinus(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, bot, character, condition, guild=None):
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        self.character = character
        self.condition = condition
        self.guild = guild
        super().__init__(style=discord.ButtonStyle.primary, emoji="➖")

    async def callback(self, interaction: discord.Interaction):
        try:
            Tracker_Model = await get_tracker_model(self.ctx, self.bot, guild=self.guild, engine=self.engine)
            await increment_cc(self.ctx, self.engine, self.character, self.condition, False, self.bot)
            output = await edit_cc_interface(self.ctx, self.engine, self.character, self.condition, self.bot)
            print(output[0])
            await interaction.response.edit_message(content=output[0], view=output[1])
            await Tracker_Model.update_pinned_tracker()
        except Exception as e:
            print(f"Error: {e}")
            logging.info(e)


class ConditionAdd(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, bot, character, condition, guild=None):
        self.ctx = ctx
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        self.bot = bot
        self.character = character
        self.condition = condition
        self.guild = guild
        super().__init__(style=discord.ButtonStyle.primary, emoji="➕")

    async def callback(self, interaction: discord.Interaction):
        try:
            Tracker_Model = await get_tracker_model(self.ctx, self.bot, guild=self.guild, engine=self.engine)
            await increment_cc(self.ctx, self.engine, self.character, self.condition, True, self.bot)
            output = await edit_cc_interface(self.ctx, self.engine, self.character, self.condition, self.bot)
            print(output[0])
            await interaction.response.edit_message(content=output[0], view=output[1])
            await Tracker_Model.update_pinned_tracker()
        except Exception as e:
            print(f"Error: {e}")
            logging.info(e)