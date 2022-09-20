import discord

import os
from dotenv import load_dotenv

# define global variables

load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
    USERNAME = os.getenv('Username')
    PASSWORD = os.getenv('Password')
    HOSTNAME = os.getenv('Hostname')
    PORT = os.getenv('PGPort')
    error_channel = os.getenv('error_channel')
else:
    TOKEN = os.getenv('BETA_TOKEN')
    USERNAME = os.getenv('BETA_Username')
    PASSWORD = os.getenv('BETA_Password')
    HOSTNAME = os.getenv('BETA_Hostname')
    PORT = os.getenv('BETA_PGPort')
    error_channel = os.getenv('BETA_error_channel')

GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
DATABASE = os.getenv('DATABASE')
error_server = os.getenv('error_server')

class ErrorReport:
    def __init__(self, ctx: discord.ApplicationContext, function_name:str, error:str):
        self.ctx = ctx
        self.name = function_name
        self.error_text = error


    async def report(self):
        guild_id = self.ctx.guild.id
        user_id = self.ctx.user.id
        self.ctx.
        output_string = f"```\n" \
                        f"Guild: {guild_id}\n" \
                        f"User: {user_id}"\
                        f""\
                        f"```"

