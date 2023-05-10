import logging

import discord
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import database_operations
from Base.Character import Character
from database_models import get_tracker
from utils.utils import get_guild


async def get_RED_Character(char_name, ctx, guild=None, engine=None):
    if engine is None:
        engine = database_operations.engine
    guild = await get_guild(ctx, guild)
    RED_tracker = await get_tracker(ctx, engine, id=guild.id)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(RED_tracker).where(RED_tracker.name == char_name))
            character = result.scalars().one()
            return RED_Character(char_name, ctx, engine, character, guild=guild)

    except NoResultFound:
        return None


class RED_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, guild=None):
        super().__init__(char_name, ctx, engine, character)
        self.level = character.level
        self.humanity = character.humanity
        self.current_luck = character.current_luck
        self.stats = character.stats
        self.skills = character.skills
        self.attacks = character.attacks
        self.armor = character.armor
        self.cyber = character.cyber
        self.net = character.net
        self.macros = character.macros
        self.bonuses = character.bonuses

    async def update(self):
        logging.info(f"Updating character: {self.char_name}")
        await calculate(self.ctx, self.engine, self.char_name, guild=self.guild)
        self.character_model = await self.character()
        self.char_name = self.character_model.name
        self.id = self.character_model.id
        self.name = self.character_model.name
        self.player = self.character_model.player
        self.user = self.character_model.user
        self.current_hp = self.character_model.current_hp
        self.max_hp = self.character_model.max_hp
        self.temp_hp = self.character_model.max_hp
        self.init_string = self.character_model.init_string
        self.init = self.character_model.init

        self.level = self.character_model.level
        self.humanity = self.character_model.humanity
        self.current_luck = self.character_model.current_luck
        self.stats = self.character_model.stats
        self.skills = self.character_model.skills
        self.attacks = self.character_model.attacks
        self.armor = self.character_model.armor
        self.cyber = self.character_model.cyber
        self.net = self.character_model.net
        self.macros = self.character_model.macros
        self.bonuses = self.character_model.bonuses


async def calculate(ctx, engine, char_name, guild=None):
    return True
