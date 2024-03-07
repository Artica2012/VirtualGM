import discord

intents = discord.Intents.default()
intents.members = True
# intents.messages = True
# intents = discord.Intents.all()
bot = discord.Bot(
    intents=intents,
    allowed_mention=discord.AllowedMentions.all()
    # debug_guilds=[GUILD]
)
