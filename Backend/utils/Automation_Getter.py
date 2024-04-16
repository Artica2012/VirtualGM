import logging

from Systems.Base.Automation import Automation
from Systems.D4e.D4e_Automation import D4e_Automation
from Systems.EPF.EPF_Automation import EPF_Automation
from Systems.PF2e.PF2_Automation import PF2_Automation
from Systems.STF.STF_Automation import STF_Automation
from Systems.RED.RED_Automation import RED_Automation
from Backend.utils.utils import get_guild


async def get_automation(ctx, guild=None):
    logging.info("get_automation")
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return EPF_Automation(ctx, guild)
    elif guild.system == "PF2":
        return PF2_Automation(ctx, guild)
    elif guild.system == "D4e":
        return D4e_Automation(ctx, guild)
    elif guild.system == "STF":
        return STF_Automation(ctx, guild)
    elif guild.system == "RED":
        return RED_Automation(ctx, guild)
    else:
        return Automation(ctx, guild)
