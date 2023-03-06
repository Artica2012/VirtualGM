
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Base.Tracker import get_init_list, Tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from Base.Autocomplete import AutoComplete
from EPF.EPF_Autocomplete import EPF_Autocmplete
from PF2e.PF2_Autocomplete import PF2_Autocmplete


async def get_autocomplete(ctx, guild=None, engine=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return EPF_Autocmplete(ctx, engine, guild)
    # elif guild.system == "D4e":
    #     return await get_D4e_Tracker(ctx, engine, init_list, bot, guild=guild)
    elif guild.system == "PF2":
        return PF2_Autocmplete(ctx, engine, guild)
    else:
        return AutoComplete(ctx, engine, guild)


