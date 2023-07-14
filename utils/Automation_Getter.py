import logging

from Base.Automation import Automation
from D4e.D4e_Automation import D4e_Automation
from EPF.EPF_Automation import EPF_Automation
from PF2e.PF2_Automation import PF2_Automation
from STF.STF_Automation import STF_Automation
from RED.RED_Automation import RED_Automation
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild


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
