# macro_cog.py
# Macro-Roller Module for VirtualGM initiative Tracker
import asyncio
import os
import logging
import datetime
import inspect

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import d20

from database_models import Global, get_macro, get_tracker
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from auto_complete import character_select, macro_select, character_select_gm
from utils.utils import get_guild
from utils.Char_Getter import get_character

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


class MacroButton(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, engine, bot, character, macro):
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
        self.character = character
        self.macro = macro
        super().__init__(
            label=f"{macro.name}: {macro.macro}",
            style=discord.ButtonStyle.primary,
            custom_id=str(f"{character.id}_{macro.id}"),
        )

    async def callback(self, interaction: discord.Interaction):
        dice_result = d20.roll(self.macro.macro)
        output_string = f"{self.character.name}:\n{self.macro.name.split(':')[0]}\n{dice_result}"

        await interaction.response.send_message(output_string)


class MacroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Functions

    # Database
    async def create_macro(self, ctx: discord.ApplicationContext, character: str, macro_name: str, macro_string: str):
        logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        try:
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(ctx, engine)
            Macro = await get_macro(ctx, engine)

            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == character))
                char = result.scalars().one()

            async with async_session() as session:
                result = await session.execute(
                    select(Macro).where(Macro.character_id == char.id).where(Macro.name == macro_name)
                )
                name_check = result.scalars().all()
                if len(name_check) > 0:
                    await ctx.channel.send(
                        "Duplicate Macro Name. Please use a different name or delete the old macro first"
                    )
                    return False

            async with session.begin():
                new_macro = Macro(character_id=char.id, name=macro_name, macro=macro_string)
                session.add(new_macro)
            await session.commit()
            await engine.dispose()
            return True
        except Exception as e:
            print(f"create_macro: {e}")
            report = ErrorReport(ctx, self.create_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def mass_add(self, ctx: discord.ApplicationContext, character: str, data: str):
        logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        try:
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(ctx, engine)
            Macro = await get_macro(ctx, engine)

            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == character))
                char = result.scalars().one()

            async with async_session() as session:
                result = await session.execute(select(Macro.name).where(Macro.character_id == char.id))
                macro_list = result.scalars().all()

            # Process data
            processed_data = data.split(";")
            # print(processed_data)
            error_list = []
            async with session.begin():
                for row in processed_data[:-1]:
                    await asyncio.sleep(0)
                    macro_split = row.split(",")
                    if macro_split[0].strip() in macro_list:
                        error_list.append(macro_split[0].strip())
                    else:
                        macro_list.append(macro_split[0].strip())
                        new_macro = Macro(
                            character_id=char.id, name=macro_split[0].strip(), macro=macro_split[1].strip()
                        )
                        session.add(new_macro)
            await session.commit()
            await engine.dispose()
            if len(error_list) > 0:
                await ctx.channel.send(f"Unable to add following macros due to duplicate names:\n{error_list}")
            return True
        except Exception as e:
            print(f"mass_add: {e}")
            report = ErrorReport(ctx, self.create_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def delete_macro(self, ctx: discord.ApplicationContext, character: str, macro_name: str):
        logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)
        Macro = await get_macro(ctx, engine)

        try:
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == character))
                char = result.scalars().one()
            async with async_session() as session:
                result = await session.execute(
                    select(Macro).where(Macro.character_id == char.id).where(Macro.name == macro_name.split(":")[0])
                )
                con = result.scalars().one()
                await session.delete(con)
                await session.commit()

            await engine.dispose()
            return True
        except Exception as e:
            print(f"delete_macro: {e}")
            report = ErrorReport(ctx, self.delete_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def delete_macro_all(self, ctx: discord.ApplicationContext, character: str):
        logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)
        Macro = await get_macro(ctx, engine)
        try:
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == character))
                char = result.scalars().one()
            async with async_session() as session:
                result = await session.execute(select(Macro).where(Macro.character_id == char.id))
                con = result.scalars().all()
            for row in con:
                await asyncio.sleep(0)
                async with async_session() as session:
                    await session.delete(row)
                    await session.commit()

            await engine.dispose()
            return True
        except Exception as e:
            print(f"delete_macro: {e}")
            report = ErrorReport(ctx, self.delete_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def roll_macro(
        self, ctx: discord.ApplicationContext, character: str, macro_name: str, dc: int, modifier: str, guild=None
    ):
        logging.info(f"roll_macro {character}, {macro_name}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, guild)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Macro = await get_macro(ctx, engine, id=guild.id)

        if guild.system == "EPF":
            logging.info("EPF")
            model = await get_character(character, ctx, guild=guild, engine=engine)
            dice_result = await model.roll_macro(macro_name, modifier)
            output_string = f"{character}:\n{macro_name}\n{dice_result}"

        else:
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == character))
                char = result.scalars().one()
            async with async_session() as session:
                result = await session.execute(
                    select(Macro).where(Macro.character_id == char.id).where(Macro.name == macro_name.split(":")[0])
                )
            try:
                macro_data = result.scalars().one()
            except Exception:
                async with async_session() as session:
                    result = await session.execute(
                        select(Macro).where(Macro.character_id == char.id).where(Macro.name == macro_name.split(":")[0])
                    )
                    macro_list = result.scalars().all()
                # print(macro_list)
                macro_data = macro_list[0]
                await ctx.channel.send(
                    "Error: Duplicate Macros with the Same Name. Rolling one macro, but please ensure that you do not have"
                    " duplicate names."
                )

            if modifier != "":
                if modifier[0] == "+" or modifier[0] == "-":
                    macro_string = macro_data.macro + modifier
                else:
                    macro_string = macro_data.macro + "+" + modifier
            else:
                macro_string = macro_data.macro

            dice_result = d20.roll(macro_string)
            output_string = f"{character}:\n{macro_name.split(':')[0]}\n{dice_result}"

        return output_string

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Slash commands

    macro = SlashCommandGroup("macro", "Macro Commands")

    @macro.command(description="Create Macro")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    async def create(self, ctx: discord.ApplicationContext, character: str, macro_name: str, macro: str):
        await ctx.response.defer(ephemeral=True)
        result = await self.create_macro(ctx, character, macro_name, macro)
        if result:
            await ctx.send_followup(f"Macro Created:\n{character}:{macro_name}: {macro}", ephemeral=True)
        else:
            await ctx.send_followup("Macro Creation Failed", ephemeral=True)

    @macro.command(description="Delete Macro")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    @option(
        "macro",
        description="Macro Name",
        autocomplete=macro_select,
    )
    async def remove(self, ctx: discord.ApplicationContext, character: str, macro: str):
        result = await self.delete_macro(ctx, character, macro)
        if result:
            await ctx.respond("Macro Deleted Successfully", ephemeral=True)
        else:
            await ctx.respond("Delete Action Failed", ephemeral=True)

    @macro.command(description="Delete All Macros")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    async def remove_all(self, ctx: discord.ApplicationContext, character: str):
        result = await self.delete_macro_all(ctx, character)
        if result:
            await ctx.respond("Macro Deleted Successfully", ephemeral=True)
        else:
            await ctx.respond("Delete Action Failed", ephemeral=True)

    @macro.command(description="Mass Import")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    @option("data", description="Import CSV data", required=True)
    async def bulk_create(self, ctx: discord.ApplicationContext, character: str, data: str):
        result = await self.mass_add(ctx, character, data)
        if result:
            await ctx.respond("Macros Created Successfully", ephemeral=True)
        else:
            await ctx.respond("Action Failed", ephemeral=True)

    @macro.command(description="Display Macros")
    @option(
        "character",
        description="Character",
        autocomplete=character_select_gm,
    )
    async def show(self, ctx: discord.ApplicationContext, character: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        await ctx.response.defer(ephemeral=True)
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
        Macro = await get_macro(ctx, engine, id=guild.id)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(
                select(Macro).where(Macro.character_id == character.id).order_by(Macro.name.asc())
            )
            macro_list = result.scalars().all()

            view = discord.ui.View(timeout=None)
            for row in macro_list:
                await asyncio.sleep(0)
                button = MacroButton(ctx, engine, self.bot, character, row)
                if len(view.children) == 24:
                    await ctx.send_followup(f"{character.name}: Macros", view=view, ephemeral=True)
                    view.clear_items()
                view.add_item(button)
            await ctx.send_followup(f"{character.name}: Macros", view=view, ephemeral=True)

    @commands.slash_command(name="m", description="Roll Macro")
    @option(
        "character",
        description="Character",
        autocomplete=character_select_gm,
    )
    @option(
        "macro",
        description="Macro Name",
        autocomplete=macro_select,
    )
    @option("modifier", description="Modifier to the macro (defaults to +)", required=False)
    @option("secret", choices=["Secret", "Open"])
    @option("dc", description="Number to which dice result will be compared", required=False)
    async def roll_macro_command(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        macro: str,
        modifier: str = "",
        dc: int = 0,
        secret: str = "Open",
    ):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        try:
            if secret == "Open":
                await ctx.send_followup(await self.roll_macro(ctx, character, macro, dc, modifier, guild=guild))
            else:
                if guild.gm_tracker_channel is not None:
                    await ctx.send_followup(f"Secret Dice Rolled.{character}: {macro}")
                    await self.bot.get_channel(int(guild.gm_tracker_channel)).send(
                        f"Secret Roll:\n{await self.roll_macro(ctx, character, macro, dc, modifier, guild=guild)}"
                    )
                else:
                    await ctx.send_followup("No GM Channel Initialized. Secret rolls not possible", ephemeral=True)
                    await ctx.channel.send(await self.roll_macro(ctx, character, macro, dc, modifier, guild=guild))
            await engine.dispose()
        except Exception as e:
            print(f"roll_macro: {e}")
            report = ErrorReport(ctx, "roll_macro", e, self.bot)
            await report.report()
            await ctx.send_followup("Macro Roll Failed")


def setup(bot):
    bot.add_cog(MacroCog(bot))
