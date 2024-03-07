import logging

import discord
from sqlalchemy import select, false, not_, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Backend.Database.database_models import get_tracker, get_macro, get_condition, Character_Vault
from Backend.utils.Char_Getter import get_character


class AutoComplete:
    def __init__(self, ctx: discord.AutocompleteContext, engine, guild):
        self.ctx = ctx
        self.engine = engine
        self.guild = guild

    async def character_select(self, **kwargs):
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

    async def vault_search(self, **kwargs):
        # print("vault search")
        output_list = []
        if "gm" in kwargs.keys():
            gm = kwargs["gm"]
        else:
            gm = False

        # vault search
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(
                select(Character_Vault)
                .where(Character_Vault.user == self.ctx.interaction.user.id)
                .where(Character_Vault.system == self.guild.system)
                .where(Character_Vault.guild_id != self.guild.id)
            )
            vault_chars = result.scalars().all()

            for item in vault_chars:
                output_list.append(f"{item.name}, {item.guild_id}")

        if gm:
            char_list = await self.character_select(gm=gm)
            output_list.extend(char_list)
        # print("output list:", output_list)

        if self.ctx.value != "":
            val = self.ctx.value.lower()
            return [char for char in output_list if val in char.lower()]
        else:
            return output_list

    async def npc_select(self, **kwargs):
        logging.info("character_select")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine)
            async with async_session() as session:
                char_result = await session.execute(
                    select(Tracker.name).where(Tracker.player == false()).order_by(Tracker.name.asc())
                )
                character = char_result.scalars().all()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in character if val in option.lower()]
            return character
        except NoResultFound:
            return []
        except Exception as e:
            logging.warning(f"character_select: {e}")

            return []

    async def add_condition_select(self, **kwargs):
        # await self.engine.dispose()
        return []

    async def macro_select(self, **kwargs):
        if "attk" in kwargs.keys():
            attk = kwargs["attk"]
        else:
            attk = False

        character = self.ctx.options["character"]
        char_split = character.split(",")
        if len(char_split) > 1:
            character = char_split[0]

        Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        try:
            async with async_session() as session:
                char_result = await session.execute(select(Tracker.id).where(Tracker.name == character))
                char = char_result.scalars().one()

            async with async_session() as session:
                if not attk:
                    macro_result = await session.execute(
                        select(Macro.name).where(Macro.character_id == char).order_by(Macro.name.asc())
                    )
                else:
                    macro_result = await session.execute(
                        select(Macro.name)
                        .where(Macro.character_id == char)
                        .where(not_(Macro.macro.contains(",")))
                        .order_by(Macro.name.asc())
                    )
                macro_list = macro_result.scalars().all()
            # await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in macro_list if val in option.lower()]
            else:
                return macro_list
        except Exception as e:
            logging.warning(f"a_macro_select: {e}")
            # await self.engine.dispose()
            return []

    async def cc_select(self, **kwargs):
        character = self.ctx.options["character"]

        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Character_Model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                result = await session.execute(
                    select(Condition.title)
                    .where(Condition.character_id == Character_Model.id)
                    .where(Condition.visible == true())
                    .order_by(Condition.title.asc())
                )
                condition = result.scalars().all()
            # await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in condition if val in option.lower()]
            else:
                return condition
        except NoResultFound:
            # await self.engine.dispose()
            return []
        except Exception as e:
            logging.warning(f"cc_select: {e}")
            # await self.engine.dispose()
            return []

    async def save_select(self, **kwargs):
        # await self.engine.dispose()
        return []

    async def get_attributes(self, **kwargs):
        logging.info("get_attributes")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            target = self.ctx.options["target"]
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == target))
                tar_char = result.scalars().one()
            async with async_session() as session:
                result = await session.execute(
                    select(Condition.title)
                    .where(Condition.character_id == tar_char.id)
                    .where(Condition.visible == false())
                )
                invisible_conditions = result.scalars().all()
            # await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in invisible_conditions if val in option.lower()]
            else:
                return invisible_conditions

        except Exception as e:
            logging.warning(f"get_attributes, {e}")
            # await self.engine.dispose()
            return []

    async def attacks(self, **kwargs):
        # await self.engine.dispose()
        return ["Not Available for this system"]

    async def stats(self, **kwargs):
        # await self.engine.dispose()
        return ["Not Available for this system"]

    async def dmg_types(self, **kwargs):
        # await self.engine.dispose()
        return ["Not Available for this system"]

    async def npc_lookup(self, **kwargs):
        # await self.engine.dispose()
        return ["Not Available for this system"]

    async def spell_list(self, **kwargs):
        # await self.engine.dispose()
        return ["Not Available for this system"]

    async def spell_level(self, **kwargs):
        # await self.engine.dispose()
        return ["Not Available for this system"]

    async def init(self, **kwargs):
        # await self.engine.dispose()
        return []

    async def flex(self, **kwargs):
        # await self.engine.dispose()
        return ["Decrement at beginning of the Turn", "Decrement at end of the Turn"]
