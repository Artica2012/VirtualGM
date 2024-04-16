import logging

from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound

from Backend.Database.database_models import get_tracker
from Backend.Database.engine import async_session
from Backend.utils.utils import get_guild
from Systems.Base.Character import Character
from Systems.D4e.D4e_Character import get_D4e_Character
from Systems.EPF.EPF_Character import get_EPF_Character
from Systems.PF2e.PF2_Character import get_PF2_Character
from Systems.RED.RED_Character import get_RED_Character
from Systems.STF.STF_Character import get_STF_Character


async def get_character(char_name, ctx, guild=None):
    """
    Function to asynchronously query the database and then populate a character model. Intelligently supplies the proper
    model depending on the system.

    :param char_name: string
    :param ctx:
    :param guild:
    :return: Character model of the appropriate subclass
    """
    logging.info("get_character")
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return await get_EPF_Character(char_name, ctx, guild=guild)
    elif guild.system == "D4e":
        return await get_D4e_Character(char_name, ctx, guild=guild)
    elif guild.system == "PF2":
        return await get_PF2_Character(char_name, ctx, guild=guild)
    elif guild.system == "STF":
        return await get_STF_Character(char_name, ctx, guild=guild)
    elif guild.system == "RED":
        return await get_RED_Character(char_name, ctx, guild=guild)
    else:
        tracker = await get_tracker(ctx, id=guild.id)
        try:
            async with async_session() as session:
                result = await session.execute(select(tracker).where(func.lower(tracker.name) == char_name.lower()))
                character = result.scalars().one()
            return Character(char_name, ctx, character, guild=guild)
        except NoResultFound:
            return None
