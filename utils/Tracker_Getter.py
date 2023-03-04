
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Generic.Tracker import get_init_list, Tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from EPF.EPF_Tracker import get_EPF_Tracker
from D4e.D4e_Tracker import get_D4e_Tracker


async def get_tracker_model(ctx, bot, guild=None, engine=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    init_list = await get_init_list(ctx, engine, guild)
    if guild.system == "EPF":
        return await get_EPF_Tracker(ctx, engine, init_list, bot, guild=guild)
    elif guild.system == "D4e":
        return await get_D4e_Tracker(ctx, engine, init_list, bot, guild=guild)
    else:
        return Tracker(ctx, engine, init_list, bot, guild=guild)


