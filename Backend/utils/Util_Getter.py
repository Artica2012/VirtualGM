import logging

from Backend.utils.utils import get_guild
from Systems.Base.Utilities import Utilities
from Systems.D4e.D4e_Utilities import D4e_Utilities
from Systems.EPF.EPF_Utilities import EPF_Utilities
from Systems.PF2e.PF2_utilities import PF2_Utilities
from Systems.STF.STF_Utilities import STF_Utilities


async def get_utilities(ctx, guild=None):
    logging.info("get_character")

    guild = await get_guild(ctx, guild)
    if guild.system == "D4e":
        return D4e_Utilities(ctx, guild)
    elif guild.system == "PF2":
        return PF2_Utilities(ctx, guild)
    elif guild.system == "EPF":
        return EPF_Utilities(ctx, guild)
    elif guild.system == "STF":
        return STF_Utilities(ctx, guild)
    else:
        return Utilities(ctx, guild)
