import logging
from math import ceil

import discord
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound

from Backend.Database.engine import lookup_session
from Backend.utils.AsyncCache import Cache
from Backend.utils.Char_Getter import get_character
from Systems.Base.Autocomplete import AutoComplete
from Systems.EPF import EPF_Support
from Systems.EPF.EPF_Character import get_EPF_Character
from Systems.EPF.EPF_NPC_Importer import EPF_NPC
from Systems.EPF.EPF_Support import (
    EPF_Conditions,
    EPF_Stats,
    EPF_DMG_Types,
    EPF_SKills,
    EPF_SKills_NO_SAVE,
    EPF_attributes,
)
from Systems.PF2e.pf2_functions import PF2_saves


class EPF_Autocmplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, guild):
        super().__init__(ctx, guild)

    async def character_select(self, **kwargs):
        # print("Char Select")

        if "all" in kwargs:
            allnone = kwargs["all"]
        else:
            allnone = False

        if "gm" in kwargs:
            gm = kwargs["gm"]
        else:
            gm = False

        if "multi" in kwargs:
            multi = kwargs["multi"]
        else:
            multi = False

        logging.info("character_select")
        try:
            character = await self.character_query(self.ctx.interaction.user.id, gm)
            if allnone:
                character.extend(["All PCs", "All NPCs", "All Characters"])

            if self.ctx.value != "":
                val = self.ctx.value.lower()
                if multi and val[-1] == ",":
                    return [f"{val.title()} {option}" for option in character]
                return [option.title() for option in character if val in option.lower()]
            return character

        except NoResultFound:
            return []
        except Exception as e:
            logging.warning(f"epf character_select: {e}")
            return []

    async def add_condition_select(self, **kwargs):
        key_list = list(EPF_Conditions.keys())
        key_list.sort()
        val = self.ctx.value.lower()
        if val != "":
            return [option for option in key_list if val in option.lower()]
        else:
            return key_list

    @Cache.ac_cache
    async def get_macro_list(self, character, attk):
        EPF_Char = await get_character(character, self.ctx, guild=self.guild)
        return await EPF_Char.macro_list()

    @Cache.ac_cache
    async def get_attack_list(self, character):
        EPF_Char = await get_character(character, self.ctx, guild=self.guild)
        return await EPF_Char.attack_list()

    async def macro_select(self, **kwargs):
        if "attk" in kwargs:
            attk = kwargs["attk"]
        else:
            attk = False

        if "dmg" in kwargs:
            dmg = kwargs["dmg"]
        else:
            dmg = False

        if "auto" in kwargs:
            auto = kwargs["auto"]
        else:
            auto = False

        try:
            character = self.ctx.options["character"]
            char_split = character.split(",")
            if len(char_split) > 1:
                character = char_split[0]
        except Exception:
            return []

        if character.lower() in ["all pcs", "all npcs", "all characters"]:
            return [item.title() for item in EPF_Support.EPF_SKills]

        try:
            EPF_Char = await get_character(character, self.ctx, guild=self.guild)
            macro_list = await self.get_macro_list(character, attk)
            if EPF_Char.character_model.medicine_prof > 0 and dmg:
                # print("Trained in Med")
                macro_list.append("Treat Wounds")

            if attk and auto:
                attk_list = await self.get_attack_list(character)
                if self.ctx.value != "":
                    val = self.ctx.value.lower()
                    return [option for option in attk_list if val in option.lower()]
                else:
                    return attk_list

            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in macro_list if val in option.lower()]
            else:
                if attk:
                    attk_list = await self.get_attack_list(character)
                    if EPF_Char.character_model.medicine_prof > 0 and dmg:
                        # print("Trained in Med")
                        attk_list.append("Treat Wounds")
                    return attk_list
                return macro_list
        except Exception as e:
            logging.warning(f"a_macro_select: {e}")
            return []

    async def save_select(self, **kwargs):
        return PF2_saves

    async def get_attributes(self, **kwargs):
        if self.ctx.value != "":
            # print(EPF_SKills)
            option_list = ["AC"]
            option_list.extend(EPF_SKills)
            # print(option_list)
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return EPF_attributes

    async def attacks(self, **kwargs):
        try:
            Character_Model = await get_EPF_Character(self.ctx.options["character"], self.ctx, guild=self.guild)
        except Exception:
            return []
        if self.ctx.value != "":
            option_list = await self.get_attack_list()
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return await Character_Model.attack_list()

    async def stats(self, **kwargs):
        if self.ctx.value != "":
            option_list = EPF_Stats
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return EPF_Stats

    async def dmg_types(self, **kwargs):
        if "var" in kwargs:
            var = kwargs["var"]
        else:
            var = False
        try:
            if var:
                if self.ctx.options["user_roll_str"] == "Treat Wounds":
                    return ["15", "20", "30", "40"]
        except Exception:
            return []
        if self.ctx.value != "":
            option_list = EPF_DMG_Types
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return EPF_DMG_Types

    async def npc_search(self, **kwargs):
        try:
            # print(lookup_engine)
            async with lookup_session() as session:
                result = await session.execute(
                    select(EPF_NPC.name)
                    .where(func.lower(EPF_NPC.name).contains(self.ctx.value.lower()))
                    .order_by(EPF_NPC.name.asc())
                )

                lookup_list = result.scalars().all()
            # print(f"Result {lookup_list}")
            # await lookup_engine.dispose()
            return lookup_list
        except Exception:
            # await lookup_engine.dispose()
            return []

    @Cache.ac_cache
    async def get_spell_list(self, character):
        Character = await get_EPF_Character(character, self.ctx, guild=self.guild)
        return Character.character_model.spells.keys()

    @Cache.ac_cache
    async def get_spell(self, character, spell):
        Character = await get_EPF_Character(character, self.ctx, guild=self.guild)
        return Character.get_spell(spell)

    async def spell_list(self, **kwargs):
        try:
            spell_list = await self.get_spell_list(self.ctx.options["character"])
        except Exception:
            return []
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option for option in spell_list if val in option.lower()]
        else:
            return spell_list

    async def spell_level(self, **kwargs):
        try:
            Character = await get_EPF_Character(self.ctx.options["character"], self.ctx, guild=self.guild)
            spell = await self.get_spell(self.ctx.options["character"], self.ctx.options["spell"])

        except Exception:
            return []

        try:
            try:
                if spell["tradition"] == "NPC":
                    return [spell["cast_level"]]
            except KeyError:
                pass

            try:
                min_level = spell["level"]
            except KeyError:
                min_level = spell["lvl"]

            # print(min_level)

            # Cantrips are always at max spell rank
            if min_level == 0:
                return [ceil(Character.character_model.level / 2)]
            max_level = ceil(Character.character_model.level / 2)

            if "complex" in spell:
                if "interval" in spell["heighten"]:
                    interval_level = spell["heighten"]["interval"]
                elif "set" in spell["heighten"]:
                    level_list = [min_level]
                    for key in spell["heighten"]["set"].keys():
                        level_list.append(int(key))
                    level_list.sort()
                    return level_list
                else:
                    interval_level = 1
            else:
                if spell["heightening"]["type"] == "interval":
                    interval_level = spell["heightening"]["interval"]
                elif spell["heightening"]["type"] == "fixed":
                    level_list = [min_level]
                    for key in spell["heightening"]["type"]["interval"]:
                        level_list.append(key)
                    return level_list
                else:
                    interval_level = 1

            level_list = []
            for num in range(min_level, max_level + 1, interval_level):
                level_list.append(num)
            return level_list
        except Exception:
            return []

    async def init(self, **kwargs):
        skills = EPF_SKills_NO_SAVE
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option.title() for option in skills if val in option.lower()]
        else:
            return [option.title() for option in skills]
