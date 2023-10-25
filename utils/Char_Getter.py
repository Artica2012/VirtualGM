import logging

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from D4e.D4e_Character import get_D4e_Character
from PF2e.PF2_Character import get_PF2_Character
from EPF.EPF_Character import get_EPF_Character
from RED.RED_Character import get_RED_Character
from STF.STF_Character import get_STF_Character
from Base.Character import Character
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_models import get_tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild


async def get_character(char_name, ctx, guild=None, engine=None):
    """
    Function to asynchronously query the database and then populate a character model. Intelligently supplies the proper
    model depending on the system.

    :param char_name: string
    :param ctx:
    :param guild:
    :param engine:
    :return: Character model of the appropriate subclass
    """
    logging.info("get_character")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return await get_EPF_Character(char_name, ctx, guild=guild, engine=engine)
    elif guild.system == "D4e":
        return await get_D4e_Character(char_name, ctx, guild=guild, engine=engine)
    elif guild.system == "PF2":
        return await get_PF2_Character(char_name, ctx, guild=guild, engine=engine)
    elif guild.system == "STF":
        return await get_STF_Character(char_name, ctx, guild=guild, engine=engine)
    elif guild.system == "RED":
        return await get_RED_Character(char_name, ctx, guild=guild, engine=engine)
    else:
        tracker = await get_tracker(ctx, engine, id=guild.id)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(select(tracker).where(tracker.name == char_name))
                character = result.scalars().one()
            return Character(char_name, ctx, engine, character, guild=guild)
        except NoResultFound:
            return None
