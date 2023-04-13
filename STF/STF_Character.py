import logging

import discord
from sqlalchemy import select, false
from sqlalchemy.exc import NoResultFound

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Character import Character
from database_models import get_tracker, get_condition
from database_operations import get_asyncio_db_engine
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from utils.utils import get_guild


async def get_PF2_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating STF_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    tracker = await get_tracker(ctx, engine, id=guild.id)
    Condition = await get_condition(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(tracker).where(tracker.name == char_name))
            character = result.scalars().one()
        async with async_session() as session:
            result = await session.execute(
                select(Condition)
                .where(Condition.character_id == character.id)
                .where(Condition.visible == false())
                .order_by(Condition.title.asc())
            )
            stat_list = result.scalars().all()
            # print(len(stat_list))
            stats = {"EAC": 0, "KAC": 0, "Fort": 0, "Reflex": 0, "Will": 0, "DC": 0}
            for item in stat_list:
                stats[f"{item.title}"] = item.number
            # print(stats)
            return PF2_Character(char_name, ctx, engine, character, stats, guild=guild)

    except NoResultFound:
        return None


class PF2_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, stats, guild):
        self.eac = stats["EAC"]
        self.kac = stats["KAC"]
        self.fort = stats["Fort"]
        self.reflex = stats["Reflex"]
        self.will = stats["Will"]
        super().__init__(char_name, ctx, engine, character, guild)
