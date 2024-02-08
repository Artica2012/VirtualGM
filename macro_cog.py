# macro_cog.py
# Macro-Roller Module for VirtualGM initiative Tracker
import logging

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands

from auto_complete import character_select, macro_select, character_select_gm, character_select_player

# define global variables
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA, log_roll
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport
from utils.Macro_Getter import get_macro_object
from utils.utils import get_guild


class MacroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    macro = SlashCommandGroup("macro", "Macro Commands")

    @macro.command(description="Create Macro")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    async def create(self, ctx: discord.ApplicationContext, character: str, macro_name: str, macro: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = False
        try:
            result = await Macro_Model.create_macro(character, macro_name, macro)
        except Exception as e:
            logging.warning(f"macro create {e}")
            report = ErrorReport(ctx, "/macro create", e, self.bot)
            await report.report()

        if result:
            await ctx.send_followup(f"Macro Created:\n{character}:{macro_name}: {macro}", ephemeral=True)
        else:
            await ctx.send_followup("Macro Creation Failed", ephemeral=True)
        # await engine.dispose()

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
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = False
        try:
            result = await Macro_Model.delete_macro(character, macro)
        except Exception as e:
            logging.warning(f"macro remove {e}")
            report = ErrorReport(ctx, "/macro remove", e, self.bot)
            await report.report()
        if result:
            await ctx.send_followup("Macro Deleted Successfully")
        else:
            await ctx.send_followup("Delete Action Failed")
        # await engine.dispose()

    @macro.command(description="Delete All Macros")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    async def remove_all(self, ctx: discord.ApplicationContext, character: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = False
        try:
            result = await Macro_Model.delete_macro_all(character)
        except Exception as e:
            logging.warning(f"macro remove_all {e}")
            report = ErrorReport(ctx, "/macro remove_all", e, self.bot)
            await report.report()
        if result:
            await ctx.send_followup("Macro Deleted Successfully")
        else:
            await ctx.send_followup("Delete Action Failed")
        # await engine.dispose()

    @macro.command(description="Mass Import")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    @option("data", description="Import CSV data", required=True)
    async def bulk_create(self, ctx: discord.ApplicationContext, character: str, data: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = False
        try:
            result = await Macro_Model.mass_add(character, data)
        except Exception as e:
            logging.warning(f"macro bulk_create {e}")
            report = ErrorReport(ctx, "/macro bulk_create", e, self.bot)
            await report.report()
        if result:
            await ctx.send_followup("Macros Created Successfully")
        else:
            await ctx.send_followup("Action Failed")

    # Set Variables
    @macro.command(description="Set Variables")
    @option(
        "character",
        description="Character",
        autocomplete=character_select,
    )
    @option("data", description="Variable string (var=value, var=value)", required=True)
    async def set_var(self, ctx: discord.ApplicationContext, character: str, data: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        result = False
        try:
            result = await Macro_Model.set_vars(character, data)
        except Exception as e:
            logging.warning(f"macro set_vars {e}")
            report = ErrorReport(ctx, "/macro set_vars", e, self.bot)
            await report.report()
        if result:
            await ctx.send_followup("Variables Set Successfully")
        else:
            await ctx.send_followup("Action Failed")

    @macro.command(description="Display Macros")
    @option(
        "character",
        description="Character",
        autocomplete=character_select_gm,
    )
    async def show(self, ctx: discord.ApplicationContext, character: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        try:
            await ctx.send_followup(f"{character}: Macros", view=await Macro_Model.show(character), ephemeral=True)
        except Exception as e:
            logging.warning(f"macro show {e}")
            report = ErrorReport(ctx, "/macro show", e, self.bot)
            await report.report()
            await ctx.send_followup("Error Displaying Character Sheet")

    @macro.command(description="Display Macros")
    @option(
        "character",
        description="Character",
        autocomplete=character_select_gm,
    )
    async def show_vars(self, ctx: discord.ApplicationContext, character: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        Macro_Model = await get_macro_object(ctx, engine=engine)
        try:
            await ctx.send_followup(embed=await Macro_Model.show_vars(character), ephemeral=True)
        except Exception as e:
            logging.warning(f"macro show {e}")
            report = ErrorReport(ctx, "/macro show", e, self.bot)
            await report.report()
            await ctx.send_followup("Error Displaying Variables")

    @commands.slash_command(name="m", description="Roll Macro")
    @option(
        "character",
        description="Character",
        autocomplete=character_select_player,
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

        try:
            char_split = character.split(",")
            if len(char_split) > 1:
                character = char_split[0]
                guild = await get_guild(ctx, None, id=int(char_split[1]))
            else:
                guild = await get_guild(ctx, None)
            Macro_Model = await get_macro_object(ctx, engine=engine, guild=guild)

            output = await Macro_Model.roll_macro(character, macro, dc, modifier, guild=guild)
            if type(output) != list:
                output = [output]
            output_list = []
            while len(output) > 0:
                output_list.append(output[:10])
                output = output[10:]

            if secret == "Open":
                secBool = False
                for item in output_list:
                    await ctx.send_followup(embeds=item)
            else:
                secBool = True
                if guild.gm_tracker_channel is not None:
                    await ctx.send_followup(f"Secret Dice Rolled.{character}: {macro}")
                    for item in output_list:
                        await self.bot.get_channel(int(guild.gm_tracker_channel)).send("Secret Roll:", embeds=item)
                else:
                    await ctx.send_followup("No GM Channel Initialized. Secret rolls not possible", ephemeral=True)
                    for item in output_list:
                        await ctx.channel.send(embeds=item)

            print("Logging")
            for item in output_list:
                log_output = f"{macro}:\n{item[0].fields[0].value}"
                await log_roll(guild.id, character, log_output, secret=secBool)

        except Exception as e:
            logging.error(f"roll_macro: {e}")
            report = ErrorReport(ctx, "roll_macro", e, self.bot)
            await report.report()
            await ctx.send_followup("Macro Roll Failed")


def setup(bot):
    bot.add_cog(MacroCog(bot))
