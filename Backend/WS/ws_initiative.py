import json

from sqlalchemy import select

from Backend.Database.database_models import Global
from Backend.Database.engine import async_session
from Discord.Bot import bot


async def get_user_tables(msg):
    user = msg["data"].get("user")
    output = {}
    async with async_session() as session:
        result = await session.execute(select(Global))
        all_guilds = result.scalars().all()

    for guild in all_guilds:
        try:
            if int(user) in guild.members:
                guild_info = {
                    "system": guild.system,
                    "gm": guild.gm,
                    "members": guild.members,
                }

                g = {
                    "id": guild.id,
                    "server": bot.get_guild(guild.guild_id).name,
                    "channel": bot.get_channel(guild.tracker_channel).name,
                    "guild_info": guild_info,
                }

                output[guild.id] = g

        except TypeError:
            pass
        except AttributeError:
            pass

    return json.dumps(output)
