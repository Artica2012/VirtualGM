import logging

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from API.api_utils import get_guild_by_id, gm_check, update_trackers, post_message
from Bot import bot
from database_operations import engine
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model

router = APIRouter()


class InitManage(BaseModel):
    user: int | None = None
    guild: int | None = None


class InitSet(BaseModel):
    character: str
    roll: str
    guild: int | None = None
    user: int | None = None


@router.post("/init/next")
async def init_start(request: InitManage, background_tasks: BackgroundTasks):
    guild = await get_guild_by_id(request.guild)
    Tracker_Model = await get_tracker_model(None, bot, guild=guild, engine=engine)
    try:
        await Tracker_Model.advance_initiative()
        success = True

    except Exception as e:
        logging.warning(f"api /init/next: {e}")
        success = False

    if success:
        background_tasks.add_task(Tracker_Model.block_post_init)

    return {"success": success}


@router.post("/init/end")
async def init_end(request: InitManage, background_tasks: BackgroundTasks):
    guild = await get_guild_by_id(request.guild)
    GM = gm_check(str(request.user), guild)
    if GM:
        try:
            Tracker_Model = await get_tracker_model(None, bot, guild=guild, engine=engine)
            await Tracker_Model.end()
            success = True
        except Exception as e:
            logging.warning(f"api /init/next: {e}")
            success = False
    else:
        success = False

    if success:
        background_tasks.add_task(post_message, guild, message="Initiative Ended")

    return {"success": success}


@router.post("/init/set")
async def init_set(request: InitSet, background_tasks: BackgroundTasks):
    guild = await get_guild_by_id(request.guild)
    Character_Model = await get_character(request.character, None, guild=guild, engine=engine)
    success_string = await Character_Model.set_init(request.roll)

    background_tasks.add_task(update_trackers, guild)

    return {"success": success_string, "character": request.character, "roll": request.roll, "user": request.user}
