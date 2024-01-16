import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from API.api_utils import get_guild_by_id, gm_check
from Bot import bot
from database_models import get_tracker
from database_operations import engine
from utils.Macro_Getter import get_macro_object
from utils.Tracker_Getter import get_tracker_model

router = APIRouter()


class InitManage(BaseModel):
    user: int | None = None
    guild: int | None = None


@router.post("/init/next")
async def init_start(request: InitManage):
    guild = await get_guild_by_id(request.guild)
    try:
        Tracker_Model = await get_tracker_model(None, bot, guild=guild, engine=engine)
        await Tracker_Model.next()
        success = True
    except Exception as e:
        logging.warning(f"api /init/next: {e}")
        success = False

    return {"success": success}


@router.post("/init/end")
async def init_start(request: InitManage):
    guild = await get_guild_by_id(request.guild)
    GM = gm_check(str(request.user), guild)
    if GM:
        # try:
        Tracker_Model = await get_tracker_model(None, bot, guild=guild, engine=engine)
        await Tracker_Model.end()
        success = True
        # except Exception as e:
        #     logging.warning(f"api /init/next: {e}")
        #     success = False
    else:
        success = False

    if success:
        await bot.get_channel(int(guild.tracker_channel)).send("Initiative Ended")

    return {"success": success}
