import discord
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Backend.Database.database_models import PF2_Lookup
from Backend.Database.engine import look_up_engine


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
            # print(len(data))
            # for item in data:
            # print(item.name)
        return data

    def process_data(self, data: PF2_Lookup):
        match data.endpoint:  # noqa
            case "feat":
                embed = self.feat(data)
            case "spell":
                embed = self.spell(data)
            case "item":
                embed = self.item(data)
            case "ancestry":
                embed = self.ancestry(data)
            case _:
                embed = self.default(data)

        return embed

    def default(self, data: PF2_Lookup):
        match data.endpoint:  # noqa
            case "class":
                color = discord.Color.blue()
            case "archetype":
                color = discord.Color.green()
            case "heritage":
                color = discord.Color.dark_gold()
            case "v-heritage":
                color = discord.Color.lighter_grey()
            case "background":
                color = discord.Color.dark_teal()
            case "condition":
                color = discord.Color.brand_green()
            case "trait":
                color = discord.Color.nitro_pink()
            case _:
                color = discord.Color.brand_red()

        embed = discord.Embed(
            title=data.name,
            description=data.data["description"],
            fields=[
                discord.EmbedField(name="Type: ", value=data.endpoint.title(), inline=False),
            ],
            color=color,
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
        if data.data["trad"] == "[]":
            tradition = "-"
        else:
            try:
                tradition = data.data["trad"].title()
            except Exception:
                tradition = "-"

        embed = discord.Embed(
            title=data.name,
            description=data.data["description"],
            fields=[
                discord.EmbedField(name="Type: ", value=data.endpoint.title(), inline=False),
                discord.EmbedField(name="Traditions: ", value=tradition, inline=False),
                discord.EmbedField(
                    name="Duration: ",
                    value=f"{data.data['duration'] if data.data['duration'] is not None else '-'}",
                    inline=False,
                ),
            ],
            color=discord.Color.dark_magenta(),
        )
        embed.set_footer(text=tags)
        return embed

    def item(self, data: PF2_Lookup):
        tags = ", ".join(data.data["tags"])

        embed = discord.Embed(
            title=data.name,
            description=data.data["description"],
            fields=[
                discord.EmbedField(name="Type: ", value=data.endpoint.title(), inline=False),
                discord.EmbedField(
                    name="Category: ",
                    value=f"{data.data['itemType'].title() if data.data['itemType'] is not None else '-'}",
                    inline=False,
                ),
                discord.EmbedField(
                    name="Price: ",
                    value=f"{data.data['price'] if data.data['price'] is not None else '-'}",
                    inline=False,
                ),
                discord.EmbedField(
                    name="Level: ",
                    value=f"{data.data['level'] if data.data['level'] is not None else '-'}",
                    inline=False,
                ),
            ],
            color=discord.Color.dark_teal(),
        )
        embed.set_footer(text=tags)
        return embed

    def ancestry(self, data: PF2_Lookup):
        embed = discord.Embed(
            title=data.name,
            description=data.data["description"],
            fields=[
                discord.EmbedField(name="Type: ", value=data.endpoint.title(), inline=False),
                discord.EmbedField(
                    name="Hit Points: ",
                    value=f"{data.data['hp'].title() if data.data['hp'] is not None else '-'}",
                    inline=False,
                ),
                discord.EmbedField(
                    name="Size: ",
                    value=f"{data.data['size'].title if data.data['size'] is not None else '-'}",
                    inline=False,
                ),
                discord.EmbedField(
                    name="Speed: ",
                    value=f"{data.data['speed'] if data.data['speed'] is not None else '-'}",
                    inline=False,
                ),
            ],
            color=discord.Color.dark_blue(),
        )
        return embed

        # '''
        # "feat": "feat",
        # "item": "item",
        # "spell": "spell",
        # "class": "class",
        # "archetype": "archetype",
        # "ancestry": "ancestry",
        # "heritage": "heritage",
        # "versatile heritage": "v-heritage",
        # "background": "background",
        # "condition": "condition",
        # "trait": "trait"
        # '''
