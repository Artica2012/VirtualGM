import logging

import discord
from sqlalchemy.exc import NoResultFound

from Base.Autocomplete import AutoComplete
from utils.Char_Getter import get_character
from D4e.d4e_functions import D4e_attributes


class D4e_Autocmplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, engine, guild):
        super().__init__(ctx, engine, guild)

    async def cc_select(self, no_time=False, flex=False):
        character = self.ctx.options["character"]

        try:
            Character_Model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
            condition = await Character_Model.conditions(no_time=no_time, flex=flex)
            await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in condition if val in option.lower()]
            else:
                return condition
        except NoResultFound:
            await self.engine.dispose()
            return []
        except Exception as e:
            logging.warning(f"cc_select: {e}")
            await self.engine.dispose()
            return []

    async def get_attributes(self):
        return D4e_attributes

    async def save_select(self):
        return ["Empty Intentionally"]
