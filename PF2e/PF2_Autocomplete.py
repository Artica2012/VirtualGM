import discord
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Autocomplete import AutoComplete
from PF2e.pf2_functions import PF2_saves, PF2_attributes
from database_models import NPC
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, DATABASE
from database_operations import get_asyncio_db_engine


class PF2_Autocmplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, engine, guild):
        super().__init__(ctx, engine, guild)

    async def save_select(self, **kwargs):
        await self.engine.dispose()
        return PF2_saves

    async def get_attributes(self, **kwargs):
        return PF2_attributes

    async def npc_search(self, **kwargs):
        await self.engine.dispose()
        lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        async_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(
                select(NPC.name).where(func.lower(NPC.name).contains(self.ctx.value.lower())).order_by(NPC.name.asc())
            )
            lookup_list = result.scalars().all()
        await lookup_engine.dispose()
        return lookup_list
