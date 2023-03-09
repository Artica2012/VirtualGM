import logging
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from Base.Macro import Macro
from EPF.EPF_Macro import EPF_Macro

async def get_macro_object(ctx, engine=None, guild=None):
    logging.info("get_character")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return EPF_Macro(ctx, engine, guild)
    else:
        return Macro(ctx, engine, guild)