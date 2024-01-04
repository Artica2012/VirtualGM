import logging

from RED.RED_Macro import RED_Macro
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from Base.Macro import Macro
from EPF.EPF_Macro import EPF_Macro
from STF.STF_Macro import STF_Macro
from PF2e.PF2_Macro import PF2_Macro
from D4e.D4e_Macro import D4e_Macro


async def get_macro_object(ctx, engine=None, guild=None):
    logging.info("get_character")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return EPF_Macro(ctx, engine, guild)
    elif guild.system == "D4e":
        return D4e_Macro(ctx, engine, guild)
    elif guild.system == "PF2":
        return PF2_Macro(ctx, engine, guild)
    elif guild.system == "STF":
        return STF_Macro(ctx, engine, guild)
    elif guild.system == "RED":
        return RED_Macro(ctx, engine, guild)
    else:
        return Macro(ctx, engine, guild)
