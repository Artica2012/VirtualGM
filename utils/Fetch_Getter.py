from database_operations import engine
from utils.utils import get_guild


async def fetchGetter(guildID):
    guild = await get_guild(None, guildID)
    # if guild.system == "EPF":
    #     return EPF_Macro(ctx, engine, guild)
    # elif guild.system == "D4e":
        return D4e_Macro(ctx, engine, guild)
    elif guild.system == "PF2":
        return PF2_Macro(ctx, engine, guild)
    elif guild.system == "STF":
        return STF_Macro(ctx, engine, guild)
    elif guild.system == "RED":
        return RED_Macro(ctx, engine, guild)
    else:
        return Macro(ctx, engine, guild)