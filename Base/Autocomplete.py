import logging

import discord
from sqlalchemy import select, false
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_tracker


class AutoComplete():
    def __init__(self, ctx:discord.AutocompleteContext, engine, guild):
        self.ctx = ctx
        self.engine = engine
        self.guild = guild

    async def character_select(self, gm=False):
        logging.info("character_select")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine)
            async with async_session() as session:
                if gm and self.guild.gm == self.ctx.interaction.user.id:
                    char_result = await session.execute(select(Tracker.name).order_by(Tracker.name.asc()))
                else:
                    char_result = await session.execute(
                        select(Tracker.name).where(Tracker.user == self.ctx.interaction.user.id).order_by(Tracker.name.asc())
                    )
                character = char_result.scalars().all()
            await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in character if val in option.lower()]
            return character
        except NoResultFound:
            await self.engine.dispose()
            return []
        except Exception as e:
            logging.warning(f"character_select: {e}")
            await self.engine.dispose()
            return []

    async def npc_select(self):
        logging.info("character_select")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine)
            async with async_session() as session:
                char_result = await session.execute(
                    select(Tracker.name).where(Tracker.player == false()).order_by(Tracker.name.asc())
                )
                character = char_result.scalars().all()
            await self.engine.dispose()
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                return [option for option in character if val in option.lower()]
            return character
        except NoResultFound:
            await self.engine.dispose()
            return []
        except Exception as e:
            logging.warning(f"character_select: {e}")
            await self.engine.dispose()
            return []