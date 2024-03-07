import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_tracker
from database_operations import engine


class APIFetches:
    def __init__(self, guild):
        self.guild = guild

    async def get_attributes(self, target):
        logging.info("get_attributes")
        try:
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(None, engine, id=self.guild.id)
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
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
            # await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in invisible_conditions if val in option.lower()]
            else:
                return invisible_conditions

        except Exception as e:
            logging.warning(f"get_attributes, {e}")
            # await self.engine.dispose()
            return []
