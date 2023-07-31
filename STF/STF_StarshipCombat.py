# imports
import logging

import discord
import sqlalchemy.exc
from sqlalchemy import select, or_, Column, Integer, String, Boolean, JSON, func
from sqlalchemy.ext.asyncio import AsyncSession, async_session
from sqlalchemy.orm import sessionmaker, declarative_base

from Base.Character import default_pic
from database_models import Global
from database_operations import engine
from utils.utils import get_guild


async def get_stf_starship_tracker(ctx: discord.ApplicationContext, guild):
    if ctx is None and guild is None:
        raise Exception
    if guild is None:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(
                select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id,
                    )
                )
            )
            guild = result.scalars().one()
    else:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.id == id))
            guild = result.scalars().one()

    if guild.system != "STF":
        raise Exception
    else:
        tablename = f"STF_SS_Tracker_{id}"
        logging.info(f"get_STF_SS_tracker: Guild: {id}")

        DynamicBase = declarative_base(class_registry=dict())

        class STF_SS_Tracker(DynamicBase):
            __tablename__ = tablename
            __table_args__ = {"extend_existing": True}

            id = Column(Integer(), primary_key=True, autoincrement=True)
            name = Column(String(), nullable=False, unique=True)
            init = Column(Integer(), default=0)
            player = Column(Boolean(), nullable=False)
            stats = Column(JSON())
            health = Column(JSON())
            macros = Column(JSON())
            attacks = Column(JSON())
            bonuses = Column(JSON())
            resistance = Column(JSON())
            pic = Column(String(), nullable=True)

        logging.info("get_tracker: returning STF_SS tracker")
        return STF_SS_Tracker


async def get_STF_Starship(ctx, name, guild=None):
    guild = await get_guild(ctx, guild)
    Tracker = await get_stf_starship_tracker(ctx, guild)
    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker).where(func.lower(Tracker.name) == name.lower()))
            starship = result.scalars().one()
        return StarShip(ctx, guild, starship)
    except sqlalchemy.exc.NoResultFound:
        return None


class StarShip:
    def __init__(self, ctx, guild, data):
        self.ctx = ctx
        self.guild = guild
        self.data = data
        self.stats = data.stats
        self.health = data.health
        self.bonuses = data.bonuses
        self.resistance = data.resistance
        self.pic = data.pic if data.pic is not None else default_pic

    async def update(self):
        Tracker = await get_stf_starship_tracker(self.ctx, self.guild)
        async with async_session() as session:
            result = await session.execute(select(Tracker).where(func.lower(Tracker.name) == name.lower()))
            starship = result.scalars().one()
        self.data = starship
        self.stats = starship.stats
        self.health = starship.health
        self.bonuses = starship.bonuses
        self.resistance = starship.resistance

    async def gunnery_check(self, character):
        # Gunnery Check = 1d20 + the gunner’s base attack bonus
        # or the gunner’s ranks in the Piloting skill + the gunner’s Dexterity modifier + bonuses from computer systems
        # + bonuses from the captain and science officers + range penalty
        bab_chk = character.character_model.bab
        piloting_chk = (
            character.character_model.piloting_mod
            + await self.bonus_calc("computer")
            + await self.bonus_calc("captain")
            + await self.bonus_calc("science")
        )
        if bab_chk > piloting_chk:
            return bab_chk
        else:
            return piloting_chk

    async def bonus_calc(self, item):
        if item in self.bonuses.keys():
            return int(self.bonuses[item])
        else:
            return 0


class Ship_Combat:
    def __init__(self, ctx, bot, guild):
        self.ctx = ctx
        self.bot = bot
        self.guild = guild
