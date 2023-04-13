import discord

from Base.Autocomplete import AutoComplete


class STF_Autocomplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, engine, guild):
        super().__init__(ctx, engine, guild)
