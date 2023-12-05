import aiohttp
import discord
from cache import AsyncTTL

GET_URL = "https://wanderersguide.app/api/"
endpoints = {
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
    "trait": "trait",
}


class Wanderer:
    def __init__(self, client_id, api_key):
        self.client_id = client_id
        self.api_key = api_key

    @AsyncTTL(time_to_live=3600, maxsize=50)
    async def lookup(
        self,
        category,
        query=None,
        id=None,
    ):
        print(category, query, id)
        output_list = []

        if id is None and query is not None:
            search_string = f"?name={query}"
        elif query is None and id is not None:
            search_string = f"?id={id}"
        else:
            search_string = "/all"

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": self.api_key}
            async with session.get(
                f"{GET_URL}{endpoints[category]}{search_string}", headers=headers, ssl=False
            ) as response:
                # print(response.status)
                # print(response)
                if response.status == 200:
                    data: dict = await response.json()
                    output_list.append(data)
                    # print(data)
        return output_list

    def decode_json(self, data: dict):
        output = {}
        # print(data)
        # print(len(data))
        if len(data) > 0:
            # print(type(data))
            for d in data:
                # print(type(d))
                for item in d.keys():
                    try:
                        # print(type(item))
                        # print(item)
                        title = d[item]["name"]
                        description = d[item]["description"]
                        output[title] = description[:1990]
                        # print(title)
                        # print(description)
                    except TypeError:
                        pass
        return output

    async def wander(self, category, query=None, id=None):
        output = await self.lookup(category, query, id)
        decoded_data = self.decode_json(output)
        embeds = []
        for key in decoded_data.keys():
            embed = discord.Embed(
                title=key.title(),
                description=decoded_data[key],
                color=discord.Color.random(),
            )
            embeds.append(embed)
        return embeds
