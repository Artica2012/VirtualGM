import logging

import discord
from sqlalchemy.exc import NoResultFound

from Systems.Base.Autocomplete import AutoComplete
from Backend.utils.Char_Getter import get_character
from Systems.D4e.d4e_functions import D4e_attributes, D4e_Conditions


class D4e_Autocmplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, guild):
        super().__init__(ctx, guild)

    async def cc_select(self, **kwargs):
        if "no_time" in kwargs.keys():
            no_time = kwargs["no_time"]
        else:
            no_time = False

        if "flex" in kwargs.keys():
            flex = kwargs["flex"]
        else:
            flex = False

        character = self.ctx.options["character"]

        try:
            Character_Model = await get_character(character, self.ctx, guild=self.guild)
            condition = await Character_Model.conditions(no_time=no_time, flex=flex)

            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in condition if val in option.lower()]
            else:
                return condition
        except NoResultFound:
            return []
        except Exception as e:
            logging.warning(f"cc_select: {e}")
            return []

    async def get_attributes(self, **kwargs):
        return D4e_attributes

    async def save_select(self, **kwargs):
        return ["Empty Intentionally"]

    async def flex(self, **kwargs):
        return ["Ends with Save", "Ends after set time"]

    async def add_condition_select(self, **kwargs):
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option for option in D4e_Conditions if val in option.lower()]
        else:
            return D4e_Conditions
