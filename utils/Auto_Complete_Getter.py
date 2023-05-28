from Base.Autocomplete import AutoComplete
from D4e.D4e_Autocomplete import D4e_Autocmplete
from EPF.EPF_Autocomplete import EPF_Autocmplete
from PF2e.PF2_Autocomplete import PF2_Autocmplete
from RED.RED_Autocomplete import RED_Autocomplete
from STF.STF_Autocomplete import STF_Autocomplete
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from sqlalchemy.exc import NoResultFound


async def get_autocomplete(ctx, guild=None, engine=None, id=id):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    try:
        guild = await get_guild(ctx, guild)
    except NoResultFound:
        print(id)
        guild = await get_guild(ctx, guild, id=id)

    if guild.system == "EPF":
        return EPF_Autocmplete(ctx, engine, guild)
    elif guild.system == "D4e":
        return D4e_Autocmplete(ctx, engine, guild)
    elif guild.system == "PF2":
        return PF2_Autocmplete(ctx, engine, guild)
    elif guild.system == "STF":
        return STF_Autocomplete(ctx, engine, guild)
    elif guild.system == "RED":
        return RED_Autocomplete(ctx, engine, guild)
    else:
        return AutoComplete(ctx, engine, guild)
