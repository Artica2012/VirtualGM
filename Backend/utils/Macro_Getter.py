import logging

from Backend.utils.utils import get_guild
from Systems.Base.Macro import Macro
from Systems.D4e.D4e_Macro import D4e_Macro
from Systems.EPF.EPF_Macro import EPF_Macro
from Systems.PF2e.PF2_Macro import PF2_Macro
from Systems.RED.RED_Macro import RED_Macro
from Systems.STF.STF_Macro import STF_Macro


async def get_macro_object(ctx, guild=None):
    logging.info("get_character")

    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return EPF_Macro(ctx, guild)
    elif guild.system == "D4e":
        return D4e_Macro(ctx, guild)
    elif guild.system == "PF2":
        return PF2_Macro(ctx, guild)
    elif guild.system == "STF":
        return STF_Macro(ctx, guild)
    elif guild.system == "RED":
        return RED_Macro(ctx, guild)
    else:
        return Macro(ctx, guild)
