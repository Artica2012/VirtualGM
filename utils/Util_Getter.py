import logging

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from EPF.EPF_Character import get_EPF_Character
from Generic.Character import Character
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_models import get_tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from Generic.Generic_Utilities import Utilities
from D4e.D4e_utilities import D4e_Utilities


async def get_utilities(ctx, guild=None, engine=None):
    logging.info("get_character")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    if guild.system == "D4e":
        return D4e_Utilities(ctx, guild, engine)
    else:
        return Utilities(ctx, guild, engine)

