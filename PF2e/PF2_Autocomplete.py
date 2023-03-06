import logging

import discord
from Base.Autocomplete import AutoComplete
from utils.Char_Getter import get_character
from PF2e.pf2_functions import PF2_saves, PF2_attributes


class PF2_Autocmplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, engine, guild):
        super().__init__(ctx, engine, guild)

    async def save_select(self):
        await self.engine.dispose()
        return PF2_saves

    async def get_attributes(self):
        return PF2_attributes