import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from API.api_utils import get_guild_by_id, gm_check, api_hard_lock
from database_models import get_tracker
from database_operations import engine
from utils.Char_Getter import get_character
from utils.Util_Getter import get_utilities

router = APIRouter()


class CharData(BaseModel):
    character: str
    user: int | None = None
    guild: int | None = None


@router.get("/char/query")
async def get_chars(user: str, guildid: int):
    guild = await get_guild_by_id(guildid)
    GM = gm_check(user, guild)

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(None, engine, id=guild.id)
        async with async_session() as session:
            if GM:
                char_result = await session.execute(select(Tracker.name).order_by(Tracker.name.asc()))
            else:
                # print("Not the GM")
                char_result = await session.execute(
                    select(Tracker.name).where(Tracker.user == int(user)).order_by(Tracker.name.asc())
                )
            return char_result.scalars().all()
    except NoResultFound:
        return []
    except Exception as e:
        logging.warning(
            f"api/char/query: {e}",
        )


@router.post("/char/delete")
async def char_delete(char_data: CharData):
    guild = await get_guild_by_id(char_data.guild)
    Character_Model = await get_character(char_data.character, None, guild=guild, engine=engine)
    if api_hard_lock(guild, char_data.user, Character_Model):
        try:
            Utilities = await get_utilities(None, guild, engine=engine)
            success = await Utilities.delete_character(char_data.character)
        except Exception as e:
            success = False
            logging.warning(f"api /char/delete: {e}")
    else:
        success = False

    return {
        "character": char_data.character,
        "success": success,
    }
