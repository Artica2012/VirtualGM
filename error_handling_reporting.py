import os

import discord
from dotenv import load_dotenv

# define global variables

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
    error_channel = os.getenv("error_channel")
else:
    TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")
    error_channel = os.getenv("BETA_error_channel")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")
error_server = os.getenv("error_server")


class ErrorReport:
    def __init__(self, ctx, function_name: str, error, bot):
        self.ctx = ctx
        self.name = function_name
        self.error_text = error
        self.bot = bot

    async def report(self):
        guild_id = self.ctx.interaction.guild_id

        channel = self.ctx.interaction.channel_id
        user_id = self.ctx.interaction.user.id
        output_string = (
            f"```\nGuild: {guild_id}, {self.ctx.interaction.guild.name} Channel: {channel},"
            f" {self.ctx.interaction.channel.name}\nOwner: {self.ctx.interaction.guild.owner_id},"
            f" {self.ctx.interaction.guild.owner.name}\nUser: {user_id}, {self.ctx.interaction.user.name}\nFunction:"
            f" {self.name}, {self.ctx.interaction.data}\nError: {self.error_text}```"
        )
        await self.bot.get_guild(int(error_server)).get_channel(int(error_channel)).send(output_string)


error_not_initialized = (
    "The VirtualGM Initiative Tracker is not set up in this channel, assure you are in the "
    "proper channel or run `/admin start` to setup the initiative tracker"
)
