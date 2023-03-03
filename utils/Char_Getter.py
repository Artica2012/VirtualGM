import logging

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from PF2e.pf2_enhanced_character import get_EPF_Character
from character import Character
from character_functions import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_models import get_tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild


async def get_character(char_name, ctx, guild=None, engine=None):
    logging.info("get_character")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return await get_EPF_Character(char_name, ctx, guild=guild, engine=engine)
    else:
        tracker = await get_tracker(ctx, engine, id=guild.id)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(select(tracker).where(tracker.name == char_name))
                character = result.scalars().one()
            return Character(char_name,ctx, engine, character, guild=guild)
        except NoResultFound:
            return None