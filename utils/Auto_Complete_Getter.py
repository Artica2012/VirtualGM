
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Base.Tracker import get_init_list, Tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from Base.Autocomplete import AutoComplete


async def get_autocomplete(ctx, guild=None, engine=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)

    # if guild.system == "EPF":
    #     return await get_EPF_Tracker(ctx, engine, init_list, bot, guild=guild)
    # elif guild.system == "D4e":
    #     return await get_D4e_Tracker(ctx, engine, init_list, bot, guild=guild)
    # elif guild.system == "PD2":
    #     return await get_PF2_Tracker(ctx, engine, init_list, bot, guild=guild)
    # else:
    return AutoComplete(ctx, engine, guild)


