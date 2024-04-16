import logging

import discord
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from Backend.Database.database_models import get_tracker, get_condition, Global
from Backend.Database.database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Backend.Database.database_operations import get_asyncio_db_engine
from Backend.Database.engine import async_session
from Backend.utils.Tracker_Getter import get_tracker_model
from Backend.utils.error_handling_reporting import error_not_initialized, ErrorReport
from Backend.utils.utils import get_guild


async def edit_cc_interface(ctx: discord.ApplicationContext, character: str, condition: str, bot, guild=None):
    logging.info("edit_cc_interface")
    view = discord.ui.View()
    try:
        guild = await get_guild(ctx, guild)
        Tracker = await get_tracker(ctx, id=guild.id)
        Condition = await get_condition(ctx, id=guild.id)
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
                if guild.system == "EPF":
                    output_string = f"{cond.title}: {cond.value}"
                else:
                    output_string = f"{cond.title}: {cond.number}"
                view.add_item(ConditionMinus(ctx, bot, character, condition, guild))
                view.add_item(ConditionAdd(ctx, bot, character, condition, guild))
                # print(output_string, view)
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
        Tracker = await get_tracker(ctx, id=guild.id)
        Condition = await get_condition(ctx, id=guild.id)

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

            if condition.time or condition.number is None:
                await ctx.send_followup("Unable to edit. Try again in a future update.", ephemeral=True)
                return False

            if guild.system == "EPF":
                current_value = condition.value
                if add is True:
                    condition.value = current_value + 1
                else:
                    condition.value = current_value - 1
                await session.commit()
            else:
                current_value = condition.number
                if add is True:
                    condition.number = current_value + 1
                else:
                    condition.number = current_value - 1
                await session.commit()

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
            Tracker_Model = await get_tracker_model(self.ctx, guild=self.guild)
            await interaction.response.defer()
            await increment_cc(self.ctx, self.engine, self.character, self.condition, False, self.bot)
            output = await edit_cc_interface(self.ctx, self.character, self.condition, self.bot)
            await interaction.edit_original_response(content=output[0], view=output[1])
            await Tracker_Model.update_pinned_tracker()
        except Exception as e:
            # print(f"Error: {e}")
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
        await interaction.response.defer()
        try:
            Tracker_Model = await get_tracker_model(self.ctx, guild=self.guild)
            await increment_cc(self.ctx, self.engine, self.character, self.condition, True, self.bot)
            output = await edit_cc_interface(self.ctx, self.character, self.condition, self.bot)
            await interaction.edit_original_response(content=output[0], view=output[1])
            await Tracker_Model.update_pinned_tracker()
        except Exception as e:
            # print(f"Error: {e}")
            logging.info(e)


async def update_member_list(guild_id):
    member_list = []
    Tracker = await get_tracker(None, id=guild_id)
    async with async_session() as session:
        result = await session.execute(select(Tracker))
    char_list = result.scalars().all()
    for char in char_list:
        if char.user not in member_list:
            member_list.append(char.user)

    async with async_session() as session:
        result = await session.execute(select(Global).where(Global.id == guild_id))
        active_guild = result.scalars().one()
        active_guild.members = member_list
        await session.commit()
