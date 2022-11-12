# macro_cog.py
# Macro-Roller Module for VirtualGM initiative Tracker
import asyncio
import os
import logging
import sys
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

from database_models import Global, get_macro, get_tracker
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport

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


class MacroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Functions

    # Autocomplete
    async def character_select(self, ctx: discord.AutocompleteContext):
        logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        character_list = []

        try:
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(ctx, engine)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker.name))
                character = char_result.scalars().all()
            return character

        except Exception as e:
            print(f'character_select: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return []

    async def macro_select(self, ctx: discord.AutocompleteContext):
        character = ctx.options['character']
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Tracker = await get_tracker(ctx, engine)
        Macro = await get_macro(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        try:
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(
                    Tracker.name == character
                ))
                char = char_result.scalars().one()

            # async with async_session() as session:
            #     macro_result = await session.execute(
            #         select(Macro).where(Macro.character_id == char.id).order_by(Macro.name.asc()))
            #     macro_list = macro_result.scalars().all()

            async with async_session() as session:
                macro_result = await session.execute(
                    select(Macro.name).where(Macro.character_id == char.id).order_by(Macro.name.asc()))
                macro_list = macro_result.scalars().all()
            #
            # macros = []
            # for row in macro_list:
            #     await asyncio.sleep(0)
            #     macros.append(f"{row.name}: {row.macro}")

            # await engine.dispose()
            return macro_list
        except Exception as e:
            print(f'a_macro_select: {e}')
            report = ErrorReport(ctx, self.macro_select.__name__, e, self.bot)
            await report.report()
            return False

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

            async with session.begin():
                new_macro = Macro(
                    character_id=char.id,
                    name=macro_name,
                    macro=macro_string
                )
                session.add(new_macro)
            await session.commit()
            await engine.dispose()
            return True
        except Exception as e:
            print(f'create_macro: {e}')
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

            # Process data
            processed_data = data.split(';')
            # print(processed_data)

            async with session.begin():
                for row in processed_data[:-1]:
                    await asyncio.sleep(0)
                    macro_split = row.split(',')
                    new_macro = Macro(
                        character_id=char.id,
                        name=macro_split[0].strip(),
                        macro=macro_split[1].strip()
                    )
                    session.add(new_macro)
            await session.commit()
            await engine.dispose()
            return True
        except Exception as e:
            print(f'mass_add: {e}')
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
                result = await session.execute(select(Macro)
                                               .where(Macro.character_id == char.id)
                                               .where(Macro.name == macro_name.split(':')[0])
                                               )
                con = result.scalars().one()
                await session.delete(con)
                await session.commit()

            await engine.dispose()
            return True
        except Exception as e:
            print(f'delete_macro: {e}')
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
                result = await session.execute(select(Macro)
                                               .where(Macro.character_id == char.id))
                con = result.scalars().all()
            for row in con:
                await asyncio.sleep(0)
                async with async_session() as session:
                    await session.delete(row)
                    await session.commit()

            await engine.dispose()
            return True
        except Exception as e:
            print(f'delete_macro: {e}')
            report = ErrorReport(ctx, self.delete_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def roll_macro(self, ctx: discord.ApplicationContext, character: str, macro_name: str, dc: int,
                         modifier: str):
        logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]}")
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)
        Macro = await get_macro(ctx, engine)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            char = result.scalars().one()
        async with async_session() as session:
            result = await session.execute(select(Macro)
                                           .where(Macro.character_id == char.id)
                                           .where(Macro.name == macro_name.split(':')[0]))
            macro_data = result.scalars().one()

        if modifier != '':
            if modifier[0] == '+' or modifier[0] == '-':
                macro_string = macro_data.macro + modifier
            else:
                macro_string = macro_data.macro + '+' + modifier
        else:
            macro_string = macro_data.macro

        roller = DiceRoller(macro_string)
        if dc == 0:
            dice_string = await roller.roll_dice()
            output_string = f"{character}:\n{macro_name.split(':')[0]} {macro_string}\n" \
                            f"{dice_string}"
        else:
            dice_string = await roller.opposed_roll(dc)
            output_string = f"{character}:\n{macro_name.split(':')[0]} {macro_string}\n" \
                            f"{dice_string}"
        # print(output_string)
        return output_string

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Slash commands

    macro = SlashCommandGroup("macro", "Macro Commands")

    @macro.command(description="Create Macro")
    @option("character", description="Character", autocomplete=character_select, )
    async def create(self, ctx: discord.ApplicationContext, character: str, macro_name: str, macro: str):
        await ctx.response.defer(ephemeral=True)
        result = await self.create_macro(ctx, character, macro_name, macro)
        if result:
            await ctx.send_followup(f"Macro Created:\n"
                                    f"{character}:"
                                    f"{macro_name}: {macro}", ephemeral=True)
        else:
            await ctx.send_followup("Macro Creation Failed", ephemeral=True)

    @macro.command(description="Delete Macro")
    @option("character", description="Character", autocomplete=character_select, )
    @option('macro', description="Macro Name", autocomplete=macro_select, )
    async def remove(self, ctx: discord.ApplicationContext, character: str, macro: str):
        result = await self.delete_macro(ctx, character, macro)
        if result:
            await ctx.respond("Macro Deleted Successfully", ephemeral=True)
        else:
            await ctx.respond("Delete Action Failed", ephemeral=True)

    @macro.command(description="Delete All Macros")
    @option("character", description="Character", autocomplete=character_select, )
    async def remove_all(self, ctx: discord.ApplicationContext, character: str):
        result = await self.delete_macro_all(ctx, character)
        if result:
            await ctx.respond("Macro Deleted Successfully", ephemeral=True)
        else:
            await ctx.respond("Delete Action Failed", ephemeral=True)

    @macro.command(description="Mass Import")
    @option("character", description="Character", autocomplete=character_select, )
    @option('data', description="Import CSV data", required=True)
    async def bulk_create(self, ctx: discord.ApplicationContext, character: str, data: str):
        result = await self.mass_add(ctx, character, data)
        if result:
            await ctx.respond("Macros Created Successfully", ephemeral=True)
        else:
            await ctx.respond("Action Failed", ephemeral=True)

    @commands.slash_command(name="m", description="Roll Macro")
    @option("character", description="Character", autocomplete=character_select, )
    @option('macro', description="Macro Name", autocomplete=macro_select, )
    @option('modifier', description="Modifier to the macro (defaults to +)", required=False)
    @option('secret', choices=['Secret', 'Open'])
    @option('dc', description="Number to which dice result will be compared", required=False)
    async def roll_macro_command(self, ctx: discord.ApplicationContext, character: str, macro: str, modifier: str = '',
                                 dc: int = 0,
                                 secret: str = "Open"):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        try:
            if secret == "Open":
                await ctx.send_followup(await self.roll_macro(ctx, character, macro, dc, modifier))
            else:
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
                    if guild.gm_tracker_channel != None:
                        await ctx.send_followup(f"Secret Dice Rolled."
                                                f"{character}: {macro}")
                        await self.bot.get_channel(int(guild.gm_tracker_channel)).send(f"Secret Roll:\n"
                                                                                       f"{await self.roll_macro(ctx, character, macro, dc, modifier)}")
                    else:
                        await ctx.send_followup('No GM Channel Initialized. Secret rolls not possible', ephemeral=True)
                        await ctx.channel.send(await self.roll_macro(ctx, character, macro, dc, modifier))

            await engine.dispose()
        except Exception as e:
            print(f"roll_macro: {e}")
            report = ErrorReport(ctx, "roll_macro", e, self.bot)
            await report.report()
            await ctx.send_followup("Macro Roll Failed")


def setup(bot):
    bot.add_cog(MacroCog(bot))
