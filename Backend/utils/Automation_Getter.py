import logging

from Systems.Base.Automation import Automation
from Systems.D4e.D4e_Automation import D4e_Automation
from Systems.EPF.EPF_Automation import EPF_Automation
from Systems.PF2e.PF2_Automation import PF2_Automation
from Systems.STF.STF_Automation import STF_Automation
from Systems.RED.RED_Automation import RED_Automation
from Backend.Database.database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from Backend.Database.database_operations import get_asyncio_db_engine
from Backend.utils.utils import get_guild


async def get_automation(ctx, guild=None, engine=None):
    logging.info("get_automation")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)

    if guild.system == "EPF":
        return EPF_Automation(ctx, engine, guild)
    elif guild.system == "PF2":
        return PF2_Automation(ctx, engine, guild)
    elif guild.system == "D4e":
        return D4e_Automation(ctx, engine, guild)
    elif guild.system == "STF":
        return STF_Automation(ctx, engine, guild)
    elif guild.system == "RED":
        return RED_Automation(ctx, engine, guild)
    else:
        return Automation(ctx, engine, guild)
