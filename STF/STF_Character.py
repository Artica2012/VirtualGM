import logging

import discord
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Character import Character
from database_models import get_tracker
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild


async def get_STF_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating STF_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    tracker = await get_tracker(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(tracker).where(tracker.name == char_name))
            character = result.scalars().one()
        return STF_Character(char_name, ctx, engine, character, guild=guild)

    except NoResultFound:
        return None


class STF_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, stats, guild):
        self.str_mod = character.str_mod
        self.dex_mod = character.dex_mod
        self.con_mod = character.con_mod
        self.itl_mod = character.itl_mod
        self.wis_mod = character.wis_mod
        self.cha_mod = character.cha_mod

        self.fort_mod = character.fort_mod
        self.will_mod = character.will_mod
        self.reflex_mod = character.reflex_mod

        self.acrobatics_mod = character.acrobatics_mod
        self.athletics_mod = character.athletics_mod
        self.bluff_mod = character.bluff_mod
        self.computers_mod = character.computers_mod
        self.culture_mod = character.culture_mod
        self.diplomacy_mod = character.diplomacy_mod
        self.disguise_mod = character.disguise_mod
        self.engineering_mod = character.enginering_mod
        self.intimidate_mod = character.intimidate_mod
        self.life_science_mod = character.life_science_mod
        self.medicine_mod = character.medicine_mod
        self.mysticism_mod = character.mysticism_mod
        self.perception_mod = character.perception_mod
        self.physical_science_mod = character.physical_science_mod
        self.piloting_mod = character.piloting_mod
        self.sense_motive_mod = character.sense_motive_mod
        self.sleight_of_hand_mod = character.sleight_of_hand_mod
        self.stealth_mod = character.stealth_mod
        self.survival_mod = character.survival_mod

        self.eac = character.eac
        self.kac = character.kac

        self.macros = character.macros
        self.attacks = character.attacks
        self.spells = character.spells
        self.bonuses = character.bonuses

        super().__init__(char_name, ctx, engine, character, guild)
