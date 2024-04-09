import logging

import discord

import Systems.STF.STF_Support
from Systems.Base.Autocomplete import AutoComplete
from Systems.STF.STF_Character import get_STF_Character
from Systems.STF.STF_Support import STF_Conditions, STF_Saves, STF_Stats, STF_DMG_Types, STF_Skills
from Backend.utils.Char_Getter import get_character


class STF_Autocomplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, engine, guild):
        super().__init__(ctx, engine, guild)

    async def add_condition_select(self, **kwargs):
        key_list = list(STF_Conditions.keys())
        key_list.sort()
        val = self.ctx.value.lower()
        if val != "":
            # await self.engine.dispose()
            return [option for option in key_list if val in option.lower()]
        else:
            # await self.engine.dispose()
            return key_list

    async def macro_select(self, **kwargs):
        if "attk" in kwargs.keys():
            attk = kwargs["attk"]
        else:
            attk = False

        try:
            character = self.ctx.options["character"]
            char_split = character.split(",")
            if len(char_split) > 1:
                character = char_split[0]
        except Exception:
            # await self.engine.dispose()
            return []

        try:
            STF_Char = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
            macro_list = await STF_Char.macro_list()

            # await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in macro_list if val in option.lower()]
            else:
                if attk:
                    attk_list = await STF_Char.attack_list()
                    return attk_list
                return macro_list
        except Exception as e:
            logging.warning(f"a_macro_select: {e}")
            # await self.engine.dispose()
            return []

    async def save_select(self, **kwargs):
        # await self.engine.dispose()
        return STF_Saves

    async def get_attributes(self, **kwargs):
        option_list = Systems.STF.STF_Support.STF_Attributes
        if self.ctx.value != "":
            # print(EPF_SKills)
            # print(option_list)
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return option_list

    async def attacks(self, **kwargs):
        try:
            Character_Model = await get_STF_Character(
                self.ctx.options["character"], self.ctx, guild=self.guild, engine=self.engine
            )
            # await self.engine.dispose()
        except Exception:
            # await self.engine.dispose()
            return []
        option_list = await Character_Model.attack_list()
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return option_list

    async def stats(self, **kwargs):
        # await self.engine.dispose()
        option_list = STF_Stats
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return option_list

    async def dmg_types(self, **kwargs):
        # await self.engine.dispose()
        option_list = STF_DMG_Types
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return option_list

    async def init(self, **kwargs):
        # await self.engine.dispose()
        skills = STF_Skills
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option.title() for option in skills if val in option.lower()]
        else:
            return [option.title() for option in skills]
