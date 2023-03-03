from character_functions import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Tracker import get_init_list, Tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from EPF.EPF_Tracker import get_EPF_Tracker


async def get_tracker_model(ctx, guild=None, engine=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    await get_guild(ctx, guild)
    init_list = get_init_list(ctx, engine, guild)
    if guild.system == "EPF":
        return await get_EPF_Tracker(ctx, guild=guild, engine=engine)

    else:
        return Tracker(ctx, engine, guild)


