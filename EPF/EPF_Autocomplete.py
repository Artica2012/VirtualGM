import logging
from math import ceil

import discord
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import database_operations
from Base.Autocomplete import AutoComplete
from EPF import EPF_Support
from EPF.EPF_Character import get_EPF_Character
from EPF.EPF_NPC_Importer import EPF_NPC
from EPF.EPF_Support import EPF_Conditions, EPF_Stats, EPF_DMG_Types, EPF_SKills, EPF_SKills_NO_SAVE, EPF_attributes
from PF2e.pf2_functions import PF2_saves
from database_models import get_tracker
from utils.Char_Getter import get_character


class EPF_Autocmplete(AutoComplete):
    def __init__(self, ctx: discord.AutocompleteContext, engine, guild):
        super().__init__(ctx, engine, guild)

    async def character_select(self, **kwargs):
        print("Char Select")

        if "all" in kwargs.keys():
            allnone = kwargs["all"]
        else:
            allnone = False

        if "gm" in kwargs.keys():
            gm = kwargs["gm"]
        else:
            gm = False

        if "multi" in kwargs.keys():
            multi = kwargs["multi"]
        else:
            multi = False

        logging.info("character_select")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine)
            async with async_session() as session:
                if gm and int(self.guild.gm) == self.ctx.interaction.user.id:
                    # print("You are the GM")
                    char_result = await session.execute(select(Tracker.name).order_by(Tracker.name.asc()))
                elif not gm:
                    char_result = await session.execute(select(Tracker.name).order_by(Tracker.name.asc()))
                else:
                    # print("Not the GM")
                    char_result = await session.execute(
                        select(Tracker.name)
                        .where(Tracker.user == self.ctx.interaction.user.id)
                        .order_by(Tracker.name.asc())
                    )
                character = char_result.scalars().all()
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

        if "dmg" in kwargs.keys():
            dmg = kwargs["dmg"]
        else:
            dmg = False

        if "auto" in kwargs.keys():
            auto = kwargs["auto"]
        else:
            auto = False

        try:
            character = self.ctx.options["character"]
            char_split = character.split(",")
            if len(char_split) > 1:
                character = char_split[0]
        except Exception:
            # await self.engine.dispose()
            return []

        if character.lower() in ["all pcs", "all npcs", "all characters"]:
            return [item.title() for item in EPF_Support.EPF_SKills]

        try:
            EPF_Char = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
            macro_list = await EPF_Char.macro_list()
            if EPF_Char.character_model.medicine_prof > 0 and dmg:
                # print("Trained in Med")
                macro_list.append("Treat Wounds")

            # await self.engine.dispose()

            if attk and auto:
                attk_list = await EPF_Char.attack_list()
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
                    attk_list = await EPF_Char.attack_list()
                    if EPF_Char.character_model.medicine_prof > 0 and dmg:
                        # print("Trained in Med")
                        attk_list.append("Treat Wounds")
                    return attk_list
                return macro_list
        except Exception as e:
            logging.warning(f"a_macro_select: {e}")
            # await self.engine.dispose()
            return []

    async def save_select(self, **kwargs):
        # await self.engine.dispose()
        return PF2_saves

    async def get_attributes(self, **kwargs):
        # await self.engine.dispose()
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
            Character_Model = await get_EPF_Character(
                self.ctx.options["character"], self.ctx, guild=self.guild, engine=self.engine
            )
            # await self.engine.dispose()
        except Exception:
            # await self.engine.dispose()
            return []
        if self.ctx.value != "":
            option_list = await Character_Model.attack_list()
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return await Character_Model.attack_list()

    async def stats(self, **kwargs):
        # await self.engine.dispose()
        if self.ctx.value != "":
            option_list = EPF_Stats
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return EPF_Stats

    async def dmg_types(self, **kwargs):
        if "var" in kwargs.keys():
            var = kwargs["var"]
        else:
            var = False

        # await self.engine.dispose()
        try:
            if var:
                if self.ctx.options["user_roll_str"] == "Treat Wounds":
                    return ["15", "20", "30", "40"]
        except Exception:
            # await self.engine.dispose()
            return []
        if self.ctx.value != "":
            option_list = EPF_DMG_Types
            val = self.ctx.value.lower()
            return [option for option in option_list if val in option.lower()]
        else:
            return EPF_DMG_Types

    async def npc_search(self, **kwargs):
        print("NPC Search")
        # await self.engine.dispose()
        try:
            lookup_engine = database_operations.look_up_engine
            print(lookup_engine)
            async_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
            async with async_session() as session:
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

    async def spell_list(self, **kwargs):
        try:
            Character = await get_EPF_Character(
                self.ctx.options["character"], self.ctx, engine=self.engine, guild=self.guild
            )
            spell_list = Character.character_model.spells.keys()
            # await self.engine.dispose()
        except Exception:
            # await self.engine.dispose()
            return []
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option for option in spell_list if val in option.lower()]
        else:
            return spell_list

    async def spell_level(self, **kwargs):
        try:
            Character = await get_EPF_Character(
                self.ctx.options["character"], self.ctx, engine=self.engine, guild=self.guild
            )
            spell_name = self.ctx.options["spell"]
            spell = Character.get_spell(spell_name)
            # print(spell_name)
            # print(spell)
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

            print(min_level)

            # Cantrips are always at max spell rank
            if min_level == 0:
                return [ceil(Character.character_model.level / 2)]
            max_level = ceil(Character.character_model.level / 2)

            if "complex" in spell.keys():
                if "interval" in spell["heighten"].keys():
                    interval_level = spell["heighten"]["interval"]
                elif "set" in spell["heighten"].keys():
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
            # await self.engine.dispose()
            return []

    async def init(self, **kwargs):
        # await self.engine.dispose()
        skills = EPF_SKills_NO_SAVE
        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [option.title() for option in skills if val in option.lower()]
        else:
            return [option.title() for option in skills]
