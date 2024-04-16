# reminder_cog.py
import asyncio
import datetime as dt
import logging

# imports
from datetime import datetime

import discord
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from sqlalchemy import select

from Backend.Database.database_models import Reminder
from Backend.utils.error_handling_reporting import ErrorReport
from Backend.Database.engine import async_session


class ReminderButton(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, bot, reminder: Reminder, time: str):
        self.ctx = ctx
        self.bot = bot

        super().__init__(
            label=f"{time}: {reminder.message}",
            style=discord.ButtonStyle.primary,
        )

    async def callback(self, interaction: discord.Interaction):
        output_string = "Roll your own save!"
        await interaction.response.send_message(output_string)


class ReminderCog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.reminder_check.start()

    @tasks.loop(minutes=1)
    async def reminder_check(self):
        async with async_session() as session:
            result = await session.execute(select(Reminder).where(Reminder.timestamp <= datetime.now().timestamp()))
            reminder = result.scalars().all()
        for item in reminder:
            try:
                await asyncio.sleep(0)
                this_guild = self.bot.get_guild(item.guild_id)
                # logging.warning(this_guild)
                this_channel = this_guild.get_channel(item.channel)
                # logging.warning(this_channel)
                await this_channel.send(
                    "``` Reminder ```\n"
                    f"{self.bot.get_user(int(item.user)).mention}: This is your reminder:\n"
                    f"{item.message}"
                )

            except Exception:
                logging.warning("Reminder Unable to Fire")
            async with async_session() as session:
                await session.delete(item)
                await session.commit()

    # Don't start the loop until the bot is ready
    @reminder_check.before_loop
    async def before_reminder_status(self):
        await self.bot.wait_until_ready()

    remind = SlashCommandGroup("remind", "Reminder")

    @remind.command(description="Set a Reminder")
    @option("time_unit", autocomplete=discord.utils.basic_autocomplete(["Minutes", "Hours", "Days", "Months"]))
    async def me(self, ctx: discord.ApplicationContext, number: int, time_unit: str, message: str):
        await ctx.response.defer(ephemeral=True)
        try:
            # Get the time to remind at
            if time_unit == "Minutes":
                reminder_time = dt.datetime.now() + dt.timedelta(minutes=number)
            elif time_unit == "Hours":
                reminder_time = dt.datetime.now() + dt.timedelta(hours=number)
            elif time_unit == "Days":
                reminder_time = dt.datetime.now() + dt.timedelta(days=number)
            elif time_unit == "Months":
                reminder_time = dt.datetime.now() + dt.timedelta(days=(number * 30))
            else:
                reminder_time = dt.datetime.now() + dt.timedelta(days=number)

            # Write to the database
            async with async_session() as session:
                async with session.begin():
                    new_reminder = Reminder(
                        user=str(ctx.user.id),
                        guild_id=ctx.guild_id,
                        channel=ctx.channel_id,
                        message=message,
                        timestamp=reminder_time.timestamp(),
                    )
                    session.add(new_reminder)
                await session.commit()
            await ctx.send_followup("Reminder Set")
        except Exception as e:
            logging.warning(f"remind_me: {e}")
            report = ErrorReport(ctx, "remind_me", e, self.bot)
            await report.report()
            await ctx.send_followup("Reminder Failed", ephemeral=True)

    # @remind.command(description="Show Reminders")
    # async def show(self, ctx:discord.ApplicationContext):
    #     await ctx.response.defer(ephemeral=True)
    #
    #     # try:
    #     async with async_session() as session:
    #         result = await session.execute(select(Reminder).where(Reminder.user == str(ctx.user.id)))
    #         reminder_list = result.scalars().all()
    #     view = discord.ui.View()
    #     for item in reminder_list[:24]:
    #         end_time = dt.datetime.fromtimestamp(item.timestamp)
    #         time_til = end_time - dt.datetime.now()
    #
    #         print(time_til)
    #         view.add_item(ReminderButton(ctx, self.bot, item, str(time_til)))
    #     await ctx.respond(view=view)
    #
    #
    #
    #     # except Exception as e:
    #     #     pass


def setup(bot):
    bot.add_cog(ReminderCog(bot))
