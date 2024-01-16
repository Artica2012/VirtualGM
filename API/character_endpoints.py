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

router = APIRouter()


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
