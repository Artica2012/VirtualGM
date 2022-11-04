# macro_cog.py
# Macro-Roller Module for VirtualGM initiative Tracker
import datetime
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
from error_handling_reporting import ErrorReport
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


class MacroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Functions

    # Autocomplete
    async def character_select(self, ctx: discord.AutocompleteContext):
        # print("searching characters")
        metadata = db.MetaData()
        character_list = []

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            if int(guild.gm) != int(ctx.interaction.user.id):
                gm_status = False
            else:
                gm_status = True

        try:
            emp = await get_tracker_table(ctx, metadata, self.engine)
            stmt = emp.select()
            async with self.engine.begin() as conn:
                data = []
                for row in await conn.execute(stmt):
                    await asyncio.sleep(0)
                    data.append(row)
                    # print(row)
            for row in data:
                await asyncio.sleep(0)
                if row[4] == ctx.interaction.user.id or gm_status:
                    character_list.append(row[1])
            # print(character_list)
            await self.engine.dispose()
            return character_list
        except Exception as e:
            print(f'character+select: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return False

    async def macro_select(self, ctx: discord.AutocompleteContext):
        metadata = db.MetaData()
        character = ctx.options['character']
        macro = await get_macro_table(ctx, metadata, self.engine)
        emp = await get_tracker_table(ctx, metadata, self.engine)

        try:
            char_stmt = emp.select().where(emp.c.name == character)
            # print(character)
            async with self.engine.begin() as conn:
                data = []
                macro_list = []
                for char_row in await conn.execute(char_stmt):
                    await asyncio.sleep(0)
                    data.append(char_row)
                for row in data:
                    await asyncio.sleep(0)
                    # print(row)
                    macro_stmt = macro.select().where(macro.c.character_id == row[0]).order_by(macro.c.name.asc())
                    for char_row in await conn.execute(macro_stmt):
                        # print(char_row)
                        macro_list.append(f"{char_row[2]}: {char_row[3]}")
            await self.engine.dispose()
            return macro_list
        except Exception as e:
            print(f'macro_selct: {e}')
            report = ErrorReport(ctx, self.macro_select.__name__, e, self.bot)
            await report.report()
            return False


    # Database
    async def create_macro(self, ctx: discord.ApplicationContext, character: str, macro_name: str, macro_string: str):
        metadata = db.MetaData()
        try:
            macro = await get_macro_table(ctx, metadata, self.engine)
            emp = await get_tracker_table(ctx, metadata, self.engine)

            char_stmt = emp.select().where(emp.c.name == character)
            async with self.engine.begin() as conn:
                data = []
                for char_row in await conn.execute(char_stmt):
                    await asyncio.sleep(0)
                    data.append(char_row)

                macro_stmt = macro.insert().values(
                    character_id=data[0][0],
                    name=macro_name,
                    macro=macro_string
                )
                result = await conn.execute(macro_stmt)
                await self.engine.dispose()
                return result
        except Exception as e:
            print(f'create_macro: {e}')
            report = ErrorReport(ctx, self.create_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def mass_add(self, ctx: discord.ApplicationContext, character: str, data: str):
        metadata = db.MetaData()
        try:
            macro = await get_macro_table(ctx, metadata, self.engine)
            emp = await get_tracker_table(ctx, metadata, self.engine)

            char_stmt = emp.select().where(emp.c.name == character)

            # Process data
            processed_data = data.split(';')
            print(processed_data)

            async with self.engine.begin() as conn:
                data = []
                for char_row in await conn.execute(char_stmt):
                    await asyncio.sleep(0)
                    data.append(char_row)

                for row in processed_data[:-1]:
                    await asyncio.sleep(0)
                    macro_split = row.split(',')
                    print(macro_split)
                    macro_stmt = macro.insert().values(
                        character_id=data[0][0],
                        name=macro_split[0].strip(),
                        macro=macro_split[1].strip()
                    )
                    result = await conn.execute(macro_stmt)
                await self.engine.dispose()
                return result
        except Exception as e:
            print(f'mass_add: {e}')
            report = ErrorReport(ctx, self.create_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def delete_macro(self, ctx: discord.ApplicationContext, character: str, macro_name: str):
        metadata = db.MetaData()
        macro = await get_macro_table(ctx, metadata, self.engine)
        emp = await get_tracker_table(ctx, metadata, self.engine)
        try:
            char_stmt = emp.select().where(emp.c.name == character)
            # print(character)
            async with self.engine.begin() as conn:
                data = []
                for char_row in await conn.execute(char_stmt):
                    await asyncio.sleep(0)
                    data.append(char_row)
                for row in data:
                    await asyncio.sleep(0)
                    # print(row)
                    # print(f"{row[0]}, {macro_name}")
                    macro_stmt = macro.select().where(macro.c.character_id == row[0]).where(
                        macro.c.name == macro_name.split(':')[0])
                    for char_row in await conn.execute(macro_stmt):
                        # print(char_row)
                        del_stmt = delete(macro).where(macro.c.id == char_row[0])
                        await conn.execute(del_stmt)

            await self.engine.dispose()
            return True
        except Exception as e:
            print(f'delete_macro: {e}')
            report = ErrorReport(ctx, self.delete_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def delete_macro_all(self, ctx: discord.ApplicationContext, character: str):
        metadata = db.MetaData()
        macro = await get_macro_table(ctx, metadata, self.engine)
        emp = await get_tracker_table(ctx, metadata, self.engine)
        try:
            char_stmt = emp.select().where(emp.c.name == character)
            # print(character)
            async with self.engine.begin() as conn:
                data = []
                for char_row in await conn.execute(char_stmt):
                    await asyncio.sleep(0)
                    data.append(char_row)
                for row in data:
                    await asyncio.sleep(0)
                    # print(row)
                    # print(f"{row[0]}, {macro_name}")
                    del_stmt = delete(macro).where(macro.c.character_id == row[0])
                    await conn.execute(del_stmt)
            await self.engine.dispose()
            return True
        except Exception as e:
            print(f'delete_macro: {e}')
            report = ErrorReport(ctx, self.delete_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def roll_macro(self, ctx: discord.ApplicationContext, character: str, macro_name: str, dc:int, modifier:str):
        metadata = db.MetaData()
        macro = await get_macro_table(ctx, metadata, self.engine)
        emp = await get_tracker_table(ctx, metadata, self.engine)

        char_stmt = emp.select().where(emp.c.name == character)
        # print(character)
        async with self.engine.begin() as conn:
            data = []
            for char_row in await conn.execute(char_stmt):
                await asyncio.sleep(0)
                data.append(char_row)
            for row in data:
                await asyncio.sleep(0)
                # print(row)
                # print(f"{row[0]}, {macro_name}")
                macro_stmt = macro.select().where(macro.c.character_id == row[0]).where(
                    macro.c.name == macro_name.split(':')[0])
                for char_row in await conn.execute(macro_stmt):
                    await asyncio.sleep(0)
                    # print(char_row)
                    if modifier != '':
                        if modifier[0] == '+' or modifier[0] == '-':
                            macro_string = char_row[3] + modifier
                        else:
                            macro_string = char_row[3] + '+' + modifier
                    else:
                        macro_string = char_row[3]

                    roller = DiceRoller(macro_string)
                    if dc ==0:
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
    async def roll_macro_command(self, ctx: discord.ApplicationContext, character: str, macro: str, modifier:str = '', dc:int = 0,
                                 secret: str = "Open"):
        await ctx.response.defer()
        try:
            if secret == "Open":
                await ctx.send_followup(await self.roll_macro(ctx, character, macro,dc, modifier))
            else:
                async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
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

            await self.engine.dispose()
        except Exception as e:
            print(f"roll_macro: {e}")
            report = ErrorReport(ctx, "roll_macro", e, self.bot)
            await report.report()
            await ctx.send_followup("Macro Roll Failed")


def setup(bot):
    bot.add_cog(MacroCog(bot))
