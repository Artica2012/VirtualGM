import discord.embeds
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import Base.Character
from Bot import bot
from database_models import Global
from database_operations import engine
from utils.Tracker_Getter import get_tracker_model


async def get_guild_by_id(id: int):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.id == id))
            guild_result = result.scalars().one()
            return guild_result
    except Exception:
        raise NoResultFound("No guild referenced")


def get_username_by_id(id: int):
    """
    :param id - integer:
    :return username - string or "" if no user is found:
    """
    user = bot.get_user(id)
    if user is None:
        username = ""
    else:
        try:
            username = user.name
        except Exception:
            username = ""

    return username


def gm_check(user: str, guild: Global):
    if str(user) == guild.gm:
        return True
    else:
        return False


def api_hard_lock(guild: Global, user: int, Character_Model: Base.Character.Character):
    """
    Hard lock for API calls to ensure the user is either the GM or the owner of the character.
    :param guild:
    :param user:
    :param Character_Model:
    :return boolean:
    """
    try:
        GM = gm_check(str(user), guild)
        Owner = int(user) == Character_Model.user
        if GM or Owner:
            return True
        else:
            return False
    except Exception:
        return False


async def update_trackers(guild: Global):
    Tracker_Object = await get_tracker_model(None, bot, guild=guild, engine=engine)
    await Tracker_Object.update_pinned_tracker()


async def post_message(
    guild: Global, message: str = None, embed: discord.embeds.Embed = None, embeds: list = None, gm: bool = False
):
    if gm:
        await bot.get_channel(int(guild.gm_tracker_channel)).send(content=message, embed=embed, embeds=embeds)
    else:
        await bot.get_channel(int(guild.tracker_channel)).send(content=message, embed=embed, embeds=embeds)
