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
from sqlalchemy.orm import Session

from database_models import Global, Base, TrackerTable, ConditionTable, MacroTable
from database_operations import get_db_engine
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
        self.engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Functions

    # Autocomplete
    async def character_select(self, ctx: discord.AutocompleteContext):
        metadata = db.MetaData()
        character_list = []

        with Session(self.engine) as session:
            guild = session.execute(select(Global).filter(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            ).scalar_one()
            if int(guild.gm) != int(ctx.interaction.user.id):
                gm_status = False
            else:
                gm_status = True

        try:
            emp = TrackerTable(ctx, metadata, self.engine).tracker_table()
            stmt = emp.select()
            compiled = stmt.compile()
            # print(compiled)
            with self.engine.connect() as conn:
                data = []
                for row in conn.execute(stmt):
                    data.append(row)
                    # print(row)
            for row in data:
                if row[4] == ctx.interaction.user.id or gm_status:
                    character_list.append(row[1])
            # print(character_list)
            return character_list
        except Exception as e:
            print(f'character+select: {e}')
            report = ErrorReport(ctx, self.character_select.__name__, e, self.bot)
            await report.report()
            return False

    async def macro_select(self, ctx: discord.AutocompleteContext):
        metadata = db.MetaData()
        character = ctx.options['character']
        macro = MacroTable(ctx, metadata, self.engine).macro_table()
        emp = TrackerTable(ctx, metadata, self.engine).tracker_table()

        char_stmt = emp.select().where(emp.c.name == character)
        # print(character)
        with self.engine.connect() as conn:
            data = []
            macro_list = []
            for char_row in conn.execute(char_stmt):
                data.append(char_row)
            for row in data:
                # print(row)
                macro_stmt = macro.select().where(macro.c.character_id == row[0])
                for char_row in conn.execute(macro_stmt):
                    # print(char_row)
                    macro_list.append(f"{char_row[2]}: {char_row[3]}")
        return macro_list

    # Database
    async def create_macro(self, ctx: discord.ApplicationContext, character: str, macro_name: str, macro_string: str):
        metadata = db.MetaData()
        insp = db.inspect(self.engine)
        try:
            macro = MacroTable(ctx, metadata, self.engine).macro_table()
            emp = TrackerTable(ctx, metadata, self.engine).tracker_table()

            with Session(self.engine) as session:
                guild = session.scalars(select(Global))
                for row in guild:
                    if not insp.has_table(macro.name):
                        metadata.create_all(self.engine)

            char_stmt = emp.select().where(emp.c.name == character)
            with self.engine.connect() as conn:
                data = []
                for char_row in conn.execute(char_stmt):
                    data.append(char_row)

                macro_stmt = macro.insert().values(
                    character_id=data[0][0],
                    name=macro_name,
                    macro=macro_string
                )
                result = conn.execute(macro_stmt)
                return result
        except Exception as e:
            print(f'create_macro: {e}')
            report = ErrorReport(ctx, self.create_macro.__name__, e, self.bot)
            await report.report()
            return False


    async def delete_macro(self, ctx: discord.ApplicationContext, character:str, macro_name:str):
        metadata = db.MetaData()
        macro = MacroTable(ctx, metadata, self.engine).macro_table()
        emp = TrackerTable(ctx, metadata, self.engine).tracker_table()
        try:
            char_stmt = emp.select().where(emp.c.name == character)
            # print(character)
            with self.engine.connect() as conn:
                data = []
                for char_row in conn.execute(char_stmt):
                    data.append(char_row)
                for row in data:
                    # print(row)
                    # print(f"{row[0]}, {macro_name}")
                    macro_stmt = macro.select().where(macro.c.character_id == row[0]).where(macro.c.name == macro_name.split(':')[0])
                    for char_row in conn.execute(macro_stmt):
                        # print(char_row)
                        del_stmt = delete(macro).where(macro.c.id == char_row[0])
                        conn.execute(del_stmt)
                        return True
        except Exception as e:
            print(f'delete_macro: {e}')
            report = ErrorReport(ctx, self.delete_macro.__name__, e, self.bot)
            await report.report()
            return False

    async def roll_macro(self, ctx: discord.ApplicationContext, character:str, macro_name:str):
        metadata = db.MetaData()
        macro = MacroTable(ctx, metadata, self.engine).macro_table()
        emp = TrackerTable(ctx, metadata, self.engine).tracker_table()

        char_stmt = emp.select().where(emp.c.name == character)
        # print(character)
        with self.engine.connect() as conn:
            data = []
            for char_row in conn.execute(char_stmt):
                data.append(char_row)
            for row in data:
                # print(row)
                # print(f"{row[0]}, {macro_name}")
                macro_stmt = macro.select().where(macro.c.character_id == row[0]).where(macro.c.name == macro_name.split(':')[0])
                for char_row in conn.execute(macro_stmt):
                    # print(char_row)
                    roller = DiceRoller(char_row[3])
                    dice_string = roller.roll_dice()
                    output_string = f"{character}: {macro_name}\n" \
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
    async def remove(self, ctx:discord.ApplicationContext, character: str, macro: str):
        result = await self.delete_macro(ctx, character, macro)
        if result:
            await ctx.respond("Macro Deleted Successfully", ephemeral=True)
        else:
            await ctx.respond("Delete Action Failed", ephemeral=True)

    @commands.slash_command(name="m", description="Roll Macro")
    @option("character", description="Character", autocomplete=character_select, )
    @option('macro', description="Macro Name", autocomplete=macro_select, )
    async def roll_macro_command(self, ctx: discord.ApplicationContext, character: str, macro: str):
        await ctx.response.defer()
        try:
            await ctx.send_followup(await self.roll_macro(ctx, character, macro))
        except Exception as e:
            print(f"roll_macro: {e}")
            report = ErrorReport(ctx, "roll_macro", e, self.bot)
            await report.report()
            await ctx.send_followup("Macro Roll Failed")


def setup(bot):
    bot.add_cog(MacroCog(bot))
