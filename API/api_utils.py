from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Bot import bot
from database_models import Global
from database_operations import engine


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
    if user == guild.gm:
        return True
    else:
        return False
