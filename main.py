# main.py

# imports
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# environmental variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')

# set up the bot/intents
intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

# define global variables
role_ids = ['1011880400513151058', '1011880477298278461', '1011880538199556176']


# These are custom from the server. Would probably need to set up the bot to create the roles if
# you were doing this for real

class RoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role):
        """A button for one role."""
        super().__init__(
            label=role.name,
            style=discord.ButtonStyle.primary,
            custom_id=str(role.id),
        )

    async def callback(self, interaction: discord.Interaction):
        # Function will be called any time a user clicks on the button
        # Interaction object is called when a user clicks on the button

        user = interaction.user
        role = interaction.guild.get_role(int(self.custom_id))

        if role is None:  # If the specified role doesn't exist, do nothing
            return
        if role not in user.roles:
            await user.add_roles(role)
            await interaction.response.send_message(
                f"You have been given the role {role.mention}!",
                ephemeral=True,  # Hide the text from other users
            )
        else:
            await user.remove_roles(role)
            await interaction.response.send_message(
                f'The {role.mention} role has been taken from you!',
                ephemeral=True
            )


class ButtonRoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(guild_ids=[GUILD], description="Post the button role message")
    async def post(self, ctx: discord.ApplicationContext):
        view = discord.ui.View(timeout=None)  # Keep it persistent

        for role_id in role_ids:
            role = ctx.guild.get_role(role_id)
            view.add_item(RoleButton(role))
        await ctx.respond("Click a button to assign yourself a role", view=view)

    @commands.Cog.listener()
    async def on_ready(self):
        view = discord.ui.View(timeout=None)
        guild = self.bot.get_guild(GUILD)
        for role_id in role_ids:
            role = guild.get_role(role_id)
            view.add_item(RoleButton(role))

        self.bot.add_view(view)


def setup(bot):
    bot.add_cog(ButtonRoleCog(bot))


@bot.event
async def on_ready():
    print(f"{bot.user} is connected.")


@bot.slash_command(guild_ids=[GUILD])
async def hello(ctx: discord.ApplicationContext):
    """Say Hello to the Bot"""
    await ctx.respond(f"Hello {ctx.author}!")


@bot.slash_command(name="hi", guild_ids=[GUILD])
async def global_command(ctx: discord.ApplicationContext, num: int):
    await ctx.respond(f'Your number is {num}')


@bot.slash_command(guild_ids=[GUILD])
async def joined(ctx: discord.ApplicationContext, member: discord.Member = None):
    user = member or ctx.author
    await ctx.respond(f"{user.name} joined at {discord.utils.format_dt(user.joined_at)}")

bot.load_extension("button_roles")
bot.run(TOKEN)
