from Backend.utils.utils import get_guild
from Systems.Base.API_Fetches import APIFetches
from Systems.EPF.EPF_Fetches import EPFFetches
from Systems.D4e.D4e_Fetches import D4eFetches
from Systems.PF2e.PF2_Fetches import PF2Fetches
from Systems.STF.STF_Fetches import STFFetches
from Systems.RED.RED_Fetches import REDFetches


async def fetchGetter(guildID):
    guild = await get_guild(None, guildID)

    if guild.system == "EPF":
        return EPFFetches(guild)
    elif guild.system == "D4e":
        return D4eFetches(guild)
    elif guild.system == "PF2":
        return PF2Fetches(guild)
    elif guild.system == "STF":
        return STFFetches(guild)
    elif guild.system == "RED":
        return REDFetches(guild)
    else:
        return APIFetches(guild)
