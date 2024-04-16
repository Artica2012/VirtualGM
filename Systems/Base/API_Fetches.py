import logging

from sqlalchemy import select, false

from Backend.Database.database_models import get_tracker, get_condition
from Backend.Database.database_operations import async_session


class APIFetches:
    def __init__(self, guild):
        self.guild = guild

    async def get_attributes(self, target):
        logging.info("get_attributes")
        try:
            Tracker = await get_tracker(None, id=self.guild.id)
            Condition = await get_condition(None, id=self.guild.id)
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == target))
                tar_char = result.scalars().one()
            async with async_session() as session:
                result = await session.execute(
                    select(Condition.title)
                    .where(Condition.character_id == tar_char.id)
                    .where(Condition.visible == false())
                )
                invisible_conditions = result.scalars().all()

            return invisible_conditions

        except Exception as e:
            logging.warning(f"get_attributes, {e}")
            return []

    def get_saves(self):
        return []
