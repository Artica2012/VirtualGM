from Base.Autocomplete import AutoComplete
from D4e.D4e_Autocomplete import D4e_Autocmplete
from EPF.EPF_Autocomplete import EPF_Autocmplete
from PF2e.PF2_Autocomplete import PF2_Autocmplete
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild


async def get_autocomplete(ctx, guild=None, engine=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return EPF_Autocmplete(ctx, engine, guild)
    elif guild.system == "D4e":
        return D4e_Autocmplete(ctx, engine, guild)
    elif guild.system == "PF2":
        return PF2_Autocmplete(ctx, engine, guild)
    else:
        return AutoComplete(ctx, engine, guild)
