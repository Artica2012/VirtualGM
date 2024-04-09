# Utility Endpoints
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.openapi.models import APIKey
from sqlalchemy import select, false
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Backend.API.api_utils import get_api_key, get_guild_by_id
from Backend.Database.database_models import Log
from Backend.Database.engine import engine

router = APIRouter()


@router.get("/", tags=["endpoints"])
async def root():
    return {"message": "Virtual GM"}


@router.get("/healthcheck", tags=["endpoints"])
def read_root():
    return {"status": "ok"}


@router.get("/logs")
async def get_logs(guildid: int, timestamp=None, secret=False, api_key: APIKey = Depends(get_api_key)):
    try:
        guild = await get_guild_by_id(guildid)
        if timestamp is None:
            now = datetime.utcnow()
            goal = now - timedelta(days=30)
            # print(f"{now} | {goal}")

        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            if secret:
                result = await session.execute(
                    select(Log)
                    .where(Log.guild_id == guild.id)
                    .where(Log.timestamp >= goal.timestamp())
                    .order_by(Log.timestamp.desc())
                )
            else:
                result = await session.execute(
                    select(Log)
                    .where(Log.guild_id == guild.id)
                    .where(Log.timestamp >= goal.timestamp())
                    .where(Log.secret == false())
                    .order_by(Log.timestamp.desc())
                )
            logsQuery = result.scalars().all()
            log_output = []
            for log in logsQuery:
                output = {
                    "character": log.character,
                    "message": log.message,
                    "timestamp": log.timestamp,
                    "secret": log.secret,
                }
                log_output.append(output)

        return json.dumps(log_output)
    except Exception:
        return []
