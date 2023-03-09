import logging

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Utilities import Utilities
from EPF.EPF_Character import get_EPF_Character, EPF_Character
from database_models import get_tracker


class EPF_Utilities(Utilities):
    def __init__(self, ctx, guild, engine):
        super().__init__(ctx, guild, engine)

    async def add_character(self, bot, name: str, hp: int, player_bool: bool,
                            init: str):
        await self.ctx.channel.send("Please use `/pf2 pb_import` or `/pf2 add_npc` to add a character")
        return False

    async def copy_character(self, name: str, new_name: str):
        await self.ctx.channel.send("Please use `/pf2 pb_import` or `/pf2 add_npc` to add a character")
        return False

    async def edit_attack(self, character, attack, stat, crit, dmg):
        Character_Model = await get_EPF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        try:
            attack_dict = Character_Model.character_model.attacks[attack]
            if stat is not None:
                attack_dict["stat"] = stat
            if crit is not None:
                attack_dict["crit"] = crit
            if dmg is not None:
                attack_dict["dmg"] = dmg
        except Exception as e:
            logging.error(f"EPF utilities edit attack (edit): {e}")
            return False
        try:
            EPF_Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            async with async_session() as session:
                query = await session.execute(select(EPF_Tracker).where(EPF_Tracker.name == character))
                query_char = query.scalars().one()

                attacks = query_char.attacks
                attacks[attack] = attack_dict

                await session.commit()


        except Exception as e:
            logging.error(f"EPF utilities edit attack (write): {e}")
            return False
