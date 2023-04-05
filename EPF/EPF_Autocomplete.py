import logging
from math import ceil

import discord
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Autocomplete import AutoComplete
from EPF.EPF_Character import PF2_attributes, PF2_skills, get_EPF_Character
from EPF.EPF_NPC_Importer import EPF_NPC
from EPF.EPF_Support import EPF_Conditions, EPF_Stats, EPF_DMG_Types, EPF_SKills_NO_SAVE
from PF2e.pf2_functions import PF2_saves
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, DATABASE
from database_operations import get_asyncio_db_engine
from utils.Char_Getter import get_character


class EPF_Autocmplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, engine, guild):
        super().__init__(ctx, engine, guild)

    async def add_condition_select(self):
        key_list = list(EPF_Conditions.keys())
        key_list.sort()
        val = self.ctx.value.lower()
        if val != "":
            await self.engine.dispose()
            return [option for option in key_list if val in option.lower()]
        else:
            await self.engine.dispose()
            return key_list

    async def macro_select(self, attk=False):
        character = self.ctx.options["character"]

        try:
            EPF_Char = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
            macro_list = await EPF_Char.macro_list()
            await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in macro_list if val in option.lower()]
            else:
                if attk:
                    return await EPF_Char.attack_list()
                return macro_list
        except Exception as e:
            logging.warning(f"a_macro_select: {e}")
            await self.engine.dispose()
            return []

    async def save_select(self):
        await self.engine.dispose()
        return PF2_saves

    async def get_attributes(self):
        await self.engine.dispose()
        if self.ctx.value != "":
            option_list = PF2_attributes + PF2_skills
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return PF2_attributes

    async def attacks(self):
        Character_Model = await get_EPF_Character(
            self.ctx.options["character"], self.ctx, guild=self.guild, engine=self.engine
        )
        await self.engine.dispose()
        if self.ctx.value != "":
            option_list = await Character_Model.attack_list()
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return await Character_Model.attack_list()

    async def stats(self):
        await self.engine.dispose()
        if self.ctx.value != "":
            option_list = EPF_Stats
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return EPF_Stats

    async def dmg_types(self):
        await self.engine.dispose()
        if self.ctx.value != "":
            option_list = EPF_DMG_Types
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return EPF_DMG_Types

    async def npc_search(self):
        await self.engine.dispose()
        lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
        async_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(
                select(EPF_NPC.name)
                .where(func.lower(EPF_NPC.name).contains(self.ctx.value.lower()))
                .order_by(EPF_NPC.name.asc())
            )
            lookup_list = result.scalars().all()
        await lookup_engine.dispose()
        return lookup_list

    async def spell_list(self):
        Character = await get_EPF_Character(
            self.ctx.options["character"], self.ctx, engine=self.engine, guild=self.guild
        )
        spell_list = Character.character_model.spells.keys()
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option for option in spell_list if val in option.lower()]
        else:
            return spell_list

    async def spell_level(self):
        Character = await get_EPF_Character(
            self.ctx.options["character"], self.ctx, engine=self.engine, guild=self.guild
        )
        spell_name = self.ctx.options["spell"]
        spell = Character.character_model.spells[spell_name]
        if spell["tradition"] == "NPC":
            return [spell["cast_level"]]

        min_level = spell["level"]
        if min_level == 0:
            return [ceil(Character.character_model.level / 2)]
        max_level = ceil(Character.character_model.level / 2)
        if spell["heightening"]["type"] == "interval":
            interval_level = spell["heightening"]["interval"]
        elif spell["heightening"]["type"] == "fixed":
            level_list = [min_level]
            for key in spell["heightening"]["type"]["interval"]:
                level_list.append(key)
            return level_list
        else:
            interval_level = 1
        print(min_level, max_level, interval_level)
        level_list = []
        for num in range(min_level, max_level + 1, interval_level):
            level_list.append(num)
        return level_list

    async def init(self):
        await self.engine.dispose()
        skills = EPF_SKills_NO_SAVE
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option.title() for option in skills if val in option.lower()]
        else:
            return [option.title() for option in skills]
