import logging

import discord

from Base.Autocomplete import AutoComplete
from EPF.EPF_Character import PF2_attributes, PF2_skills
from EPF.EPF_Support import EPF_Conditions
from PF2e.pf2_functions import PF2_saves
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
                return macro_list
        except Exception as e:
            logging.warning(f"a_macro_select: {e}")
            await self.engine.dispose()
            return []

    async def save_select(self):
        await self.engine.dispose()
        return PF2_saves

    async def get_attributes(self):
        if self.ctx.value != "":
            option_list = PF2_attributes + PF2_skills
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return PF2_attributes
