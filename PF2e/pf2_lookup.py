import os

import aiohttp
import discord

endpoints = [
    "action",
    "ancestry",
    "ancestry feature",
    "background",
    "class",
    "class feature",
    "deity",
    "equipment",
    "feat",
    "heritage",
    "spell",
]


async def pf2_lookup_search(category, query):
    lookup = PF2_Lookup(os.environ["LOOKUP_KEY"])
    return await lookup.lookup(query, category)


class PF2_Lookup:
    def __init__(self, key):
        self.key = key
        self.endpoints = {
            "all": "https://api.pathfinder2.fr/v1/pf2/",
            "action": "https://api.pathfinder2.fr/v1/pf2/action",
            "ancestry": "https://api.pathfinder2.fr/v1/pf2/ancestry",
            "ancestry feature": "https://api.pathfinder2.fr/v1/pf2/ancestryFeature",
            "archetype": "https://api.pathfinder2.fr/v1/pf2/archetype",
            "background": "https://api.pathfinder2.fr/v1/pf2/background",
            "class": "https://api.pathfinder2.fr/v1/pf2/class",
            "class feature": "https://api.pathfinder2.fr/v1/pf2/classFeature",
            "deity": "https://api.pathfinder2.fr/v1/pf2/deity",
            "equipment": "https://api.pathfinder2.fr/v1/pf2/equipment",
            "feat": "https://api.pathfinder2.fr/v1/pf2/feat",
            "heritage": "https://api.pathfinder2.fr/v1/pf2/heritage",
            "spell": "https://api.pathfinder2.fr/v1/pf2/spell",
        }

    async def lookup(self, query, endpoint):
        """
        :param query:
        :param endpoint:
        :return: results (list)
        """
        async with aiohttp.ClientSession() as session:
            params = {"name": query}
            headers = {"Authorization": self.key}
            async with session.get(self.endpoints[endpoint], headers=headers, params=params, ssl=False) as response:
                if response.status is not 200:
                    return []
                data: dict = await response.json()

            output_list = []
            for item in data["results"]:
                output_list.append(Result(item))
        return output_list


class Result:
    def __init__(self, data):
        self.data = data
        self.name = data["name"]
        try:
            self.description = self.remove_html_tags(data["system"]["description"]["value"])
        except KeyError:
            self.description = ""
        try:
            self.traits = data["system"]["traits"]["value"]
        except KeyError:
            self.traits = []
        self.type = data["type"]

    def remove_html_tags(self, text):
        """Remove html tags from a string"""
        import re

        clean = re.compile("<.*?>")
        clean_2 = re.compile("@.*?]")
        sub_string = re.sub(clean, "", text)
        string = re.sub(clean_2, "", sub_string)
        if len(string) > 1000:
            return f"{string[:1000]}..."
        else:
            return string

    async def get_embed(self):
        match self.type:  # noqa
            case "action":
                return await self.action_embed()
            case "ancestry":
                return await self.ancestry_embed()
            case "feat":
                return await self.feat_embed()
            case "background":
                return await self.background_embed()
            case "class":
                return await self.class_embed()
            case "deity":
                return await self.deity_embed()
            case "equipment":
                return await self.equipment_embed()
            case "weapon":
                return await self.weapon_embed()
            case "heritage":
                return await self.heritage_embed()
            case "spell":
                return await self.spell_embed()
            case _:
                return await self.generic_embed()

    async def action_embed(self):
        trait_str = ""
        for trait in self.traits:
            trait_str += f"{trait.title()}\n"

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(
                    name="Type: ", value=self.data["system"]["actionType"]["value"].title(), inline=False
                ),
                discord.EmbedField(name="Traits", value=trait_str, inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def ancestry_embed(self):
        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(name="Size: ", value=self.data["system"]["size"].title(), inline=False),
                discord.EmbedField(name="Speed: ", value=self.data["system"]["speed"], inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def feat_embed(self):
        trait_str = ""
        for trait in self.traits:
            trait_str += f"{trait.title()}\n"

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(name="Traits", value=trait_str, inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def background_embed(self):
        item_list = ""
        for key in self.data["system"]["items"].keys():
            item_list += f"{self.data['system']['items'][key]['name']}\n"

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(name="Feat: ", value=item_list.title(), inline=False),
                discord.EmbedField(name="Lore: ", value=self.data["system"]["trainedLore"].title(), inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def class_embed(self):
        ability_str = ""
        for item in self.data["system"]["keyAbility"]["value"]:
            ability_str += f"{item.title()}\n"
        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(name="Key Ability: ", value=ability_str, inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def deity_embed(self):
        domains = ""
        for item in self.data["system"]["domains"]["primary"]:
            domains += f"{item.title()}\n"

        font = ""
        for item in self.data["system"]["font"]:
            font += f"{item.title()}\n"

        weapons = ""
        for item in self.data["system"]["weapons"]:
            weapons += f"{item.title()}\n"

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(
                    name="Alignment: ",
                    value=(
                        self.data["system"]["alignment"]["own"]
                        if self.data["system"]["alignment"]["own"] is not None
                        else "None"
                    ),
                    inline=False,
                ),
                discord.EmbedField(name="Domains: ", value=domains, inline=False),
                discord.EmbedField(name="Font: ", value=font, inline=False),
                discord.EmbedField(name="Weapons: ", value=weapons, inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def equipment_embed(self):
        value = ""
        for key in self.data["system"]["price"]["value"]:
            value += f"{self.data['system']['price']['value'][key]} {key} "

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(name="Level: ", value=self.data["system"]["level"]["value"], inline=False),
                discord.EmbedField(name="Price: ", value=value, inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def weapon_embed(self):
        value = ""
        for key in self.data["system"]["price"]["value"]:
            value += f"{self.data['system']['price']['value'][key]} {key} "

        trait_str = ""
        for trait in self.traits:
            trait_str += f"{trait.title()}\n"

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(name="Level: ", value=self.data["system"]["level"]["value"], inline=False),
                discord.EmbedField(name="Proficiency: ", value=self.data["system"]["category"], inline=False),
                discord.EmbedField(name="Group: ", value=self.data["system"]["group"].title(), inline=False),
                discord.EmbedField(
                    name="Damage: ",
                    value=f"{self.data['system']['damage']['die']} {self.data['system']['damage']['damageType']}",
                    inline=False,
                ),
                discord.EmbedField(name="Usage: ", value=self.data["system"]["usage"]["value"], inline=False),
                discord.EmbedField(name="Price: ", value=value, inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def heritage_embed(self):
        trait_str = ""
        for trait in self.traits:
            trait_str += f"{trait.title()}\n"

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(name="Traits", value=trait_str, inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def spell_embed(self):
        trait_str = ""
        for trait in self.traits:
            trait_str += f"{trait.title()}\n"

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(name="Traits", value=trait_str, inline=False),
            ],
            color=discord.Color.random(),
        )
        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed

    async def generic_embed(self):
        trait_str = ""
        for trait in self.traits:
            trait_str += f"{trait.title()}\n"

        trad_str = ""
        for trad in self.data["system"]["traditions"]["value"]:
            trad_str += f"{trad.title()}\n"

        embed = discord.Embed(
            title=self.name,
            fields=[
                discord.EmbedField(name="Description: ", value=self.description, inline=False),
                discord.EmbedField(
                    name="Duration: ", value=self.data["system"]["duration"]["value"].title(), inline=False
                ),
                discord.EmbedField(name="Target: ", value=self.data["system"]["target"]["value"].title(), inline=False),
                discord.EmbedField(
                    name="Actions: ", value=f"{self.data['system']['time']['value']} actions", inline=False
                ),
                discord.EmbedField(name="Traditions: ", value=trad_str, inline=False),
                discord.EmbedField(name="School: ", value=self.data["system"]["school"]["value"], inline=False),
                discord.EmbedField(name="Traits", value=trait_str, inline=False),
            ],
            color=discord.Color.random(),
        )

        embed.set_footer(text=self.data["system"]["source"]["value"])
        return embed
