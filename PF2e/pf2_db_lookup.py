import discord
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.operators import ilike_op

from database_models import PF2_Lookup
from database_operations import look_up_engine


class WandererLookup:
    async def lookup(self, query):
        embed_list = []
        data = await self.db_query(query)
        for item in data:
            embed_list.append(self.process_data(item))

        return embed_list

    async def db_query(self, search):
        async_session = sessionmaker(look_up_engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(
                select(PF2_Lookup).where(func.lower(PF2_Lookup.name).contains(search.lower()))
            )
            # result =  await session.execute(select(PF2_Lookup))
            data = result.scalars().all()
            print(len(data))
            for item in data:
                print(item.name)
        return data

    def process_data(self, data: PF2_Lookup):
        match data.endpoint:  # noqa
            case "feat":
                embed = self.feat(data)
            case "spell":
                embed = self.spell(data)
            case _:
                embed = self.default(data)

        return embed

    def default(self, data: PF2_Lookup):
        embed = discord.Embed(
            title=data.name,
            description=data.data["description"],
            fields=[
                discord.EmbedField(name="Type: ", value=data.endpoint.title(), inline=False),
            ],
            color=discord.Color.orange(),
        )
        return embed

    def feat(self, data: PF2_Lookup):
        tags = ", ".join(data.data["tags"])

        embed = discord.Embed(
            title=data.name,
            description=data.data["description"],
            fields=[
                discord.EmbedField(name="Type: ", value=data.endpoint.title(), inline=False),
            ],
            color=discord.Color.dark_green(),
        )
        embed.set_footer(text=tags)
        return embed

    def spell(self, data: PF2_Lookup):
        tags = ", ".join(data.data["tags"])

        embed = discord.Embed(
            title=data.name,
            description=data.data["description"],
            fields=[
                discord.EmbedField(name="Type: ", value=data.endpoint.title(), inline=False),
                discord.EmbedField(name="Traditions: ", value=data.data["trad"].title(), inline=False),
                discord.EmbedField(name="Duration: ", value=data.data["duration"], inline=False),
            ],
            color=discord.Color.dark_magenta(),
        )
        embed.set_footer(text=tags)
        return embed

        """
        "feat": "feat",
        "item": "item",
        "spell": "spell",
        "class": "class",
        "archetype": "archetype",
        "ancestry": "ancestry",
        "heritage": "heritage",
        "versatile heritage": "v-heritage",
        "background": "background",
        "condition": "condition",
        "trait": "trait"
        """
