import discord
from sqlalchemy import func, select


from Systems.Base.Autocomplete import AutoComplete
from Systems.PF2e.pf2_functions import PF2_saves, PF2_attributes
from Backend.Database.database_models import NPC
from Backend.Database.engine import lookup_session


class PF2_Autocmplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, guild):
        super().__init__(ctx, guild)

    async def save_select(self, **kwargs):
        # await self.engine.dispose()
        return PF2_saves

    async def get_attributes(self, **kwargs):
        return PF2_attributes

    async def npc_search(self, **kwargs):
        async with lookup_session() as session:
            result = await session.execute(
                select(NPC.name).where(func.lower(NPC.name).contains(self.ctx.value.lower())).order_by(NPC.name.asc())
            )
            lookup_list = result.scalars().all()
        return lookup_list
