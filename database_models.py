# database_models.py

import os
import logging

import discord
import sqlalchemy as db
from dotenv import load_dotenv
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, BigInteger
from sqlalchemy import String, Boolean
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# define global variables


load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
    USERNAME = os.getenv('Username')
    PASSWORD = os.getenv('Password')
    HOSTNAME = os.getenv('Hostname')
    PORT = os.getenv('PGPort')
else:
    TOKEN = os.getenv('BETA_TOKEN')
    USERNAME = os.getenv('BETA_Username')
    PASSWORD = os.getenv('BETA_Password')
    HOSTNAME = os.getenv('BETA_Hostname')
    PORT = os.getenv('BETA_PGPort')

GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')

Base = declarative_base()


# Database Models

# Global Class
class Global(Base):
    __tablename__ = "global_manager"
    # ID Columns
    id = Column(Integer(), primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger())
    gm = Column(String())
    # Feature Flags
    explode = Column(Boolean(), default=False)
    aliases = Column(Boolean(), default=False)
    block = Column(Boolean(), default=False)
    system = Column(String(), default=None, nullable=True)
    # Initiative Tracker
    initiative = Column(Integer())
    round = Column(Integer(), default=0)
    saved_order = Column(String(), default='')
    tracker = Column(BigInteger(), nullable=True)
    tracker_channel = Column(BigInteger(), nullable=True, unique=True)
    gm_tracker = Column(BigInteger(), nullable=True)
    gm_tracker_channel = Column(BigInteger(), nullable=True, unique=True)
    rp_channel = Column(BigInteger(), nullable=True, unique=True)
    # Timekeeper Functionality
    timekeeping = Column(Boolean(), default=False)
    time = Column(BigInteger(), default=6, nullable=False)
    time_second = Column(Integer(), nullable=True)
    time_minute = Column(Integer(), nullable=True)
    time_hour = Column(Integer(), nullable=True)
    time_day = Column(Integer(), nullable=True)
    time_month = Column(Integer(), nullable=True)
    time_year = Column(Integer(), nullable=True)


#########################################
#########################################
# Tracker Table

# Tracker Get Function
async def get_tracker(ctx: discord.ApplicationContext, engine, id=None):
    if id == None:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            tablename = f"Tracker_{guild.id}"
            logging.info(f"get_tracker: Guild: {guild.id}")

    else:
        tablename = f"Tracker_{id}"

    DynamicBase = declarative_base(class_registry=dict())

    class Tracker(DynamicBase):
        __tablename__ = tablename
        __table_args__ = {'extend_existing': True}

        id = Column(Integer(), primary_key=True, autoincrement=True)
        name = Column(String(), nullable=False, unique=True)
        init = Column(Integer(), default=0)
        player = Column(Boolean(), nullable=False)
        user = Column(BigInteger(), nullable=False)
        current_hp = Column(Integer(), default=0)
        max_hp = Column(Integer(), default=1)
        temp_hp = Column(Integer(), default=0)
        init_string = Column(String(), nullable=True)

    logging.info(f"get_tracker: returning tracker")
    return Tracker


# Old Tracker Get Fuctcion
async def get_tracker_table(ctx, metadata, engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(Global).where(
            or_(
                Global.tracker_channel == ctx.interaction.channel_id,
                Global.gm_tracker_channel == ctx.interaction.channel_id
            )
        )
        )
        guild = result.scalars().one()

    table = TrackerTable(ctx, metadata, guild.id).tracker_table()
    return table


# Old Tracker (emp) Class
class TrackerTable:
    def __init__(self, ctx, metadata, id):
        self.guild = ctx.interaction.guild_id
        self.channel = ctx.interaction.channel_id
        self.metadata = metadata
        self.id = id

    def tracker_table(self):
        tablename = f"Tracker_{self.id}"
        emp = db.Table(tablename, self.metadata,
                       db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                       db.Column('name', db.String(255), nullable=False, unique=True),
                       db.Column('init', db.INTEGER(), default=0),
                       db.Column('player', db.BOOLEAN, default=False),
                       db.Column('user', db.BigInteger(), nullable=False),
                       db.Column('current_hp', db.INTEGER(), default=0),
                       db.Column('max_hp', db.INTEGER(), default=1),
                       db.Column('temp_hp', db.INTEGER(), default=0),
                       db.Column('init_string', db.String(255), nullable=True)
                       )
        return emp


#########################################
#########################################
# Condition Table

# Condition Get Function
async def get_condition(ctx: discord.ApplicationContext, engine, id=None):
    if id == None:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            tablename = f"Condition_{guild.id}"
            logging.info(f"get_condition: Guild: {guild.id}")

    else:
        tablename = f"Condition_{id}"

    DynamicBase = declarative_base(class_registry=dict())

    class Condition(DynamicBase):
        __tablename__ = tablename
        __table_args__ = {'extend_existing': True}

        id = Column(Integer(), primary_key=True, autoincrement=True)
        character_id = Column(Integer(), nullable=False)
        counter = Column(Boolean(), default=False)
        title = Column(String(), nullable=False)
        number = Column(Integer(), nullable=True, default=False)
        auto_increment = Column(Boolean(), nullable=False, default=False)
        time = Column(Boolean(), default=False)
        visible = Column(Boolean(), default=True)
        flex = Column(Boolean(), default=False)

    logging.info(f"get_condition: returning condition")
    return Condition


async def get_condition_table(ctx, metadata, engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(Global).where(
            or_(
                Global.tracker_channel == ctx.interaction.channel_id,
                Global.gm_tracker_channel == ctx.interaction.channel_id
            )
        )
        )
        guild = result.scalars().one()

    table = ConditionTable(ctx, metadata, guild.id).condition_table()
    return table


class ConditionTable:
    def __init__(self, ctx, metadata, id):
        self.metadata = metadata
        self.id = id

    def condition_table(self, ):
        tablename = f"Condition_{self.id}"
        con = db.Table(tablename, self.metadata,
                       db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                       db.Column('character_id', db.INTEGER(), ForeignKey(f'Tracker_{self.id}.id')),
                       db.Column('counter', db.BOOLEAN(), default=False),
                       db.Column('title', db.String(255), nullable=False),
                       db.Column('number', db.INTEGER(), nullable=True, default=None),
                       db.Column('auto_increment', db.BOOLEAN, nullable=False, default=False),
                       db.Column('time', db.BOOLEAN, default=False),
                       db.Column('visible', db.BOOLEAN, default=True),
                       db.Column('flex', db.BOOLEAN, default=False)
                       )
        return con


#########################################
#########################################
# Macro Table

class Macro(Base):
    __abstract__ = True
    __table_args__ = {'extend_existing': True}

    id = Column(Integer(), primary_key=True, autoincrement=True)
    character_id = Column(Integer(), nullable=False)
    name = Column(String(), nullable=False, unique=False)
    macro = Column(String(), nullable=False, unique=False)


async def get_macro(ctx: discord.ApplicationContext, engine, id=None):
    if id == None:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            logging.info(f"get_macro: Guild: {guild.id}")
            tablename = f"Macro_{guild.id}"

    else:
        tablename = f"Macro_{id}"

    DynamicBase = declarative_base(class_registry=dict())

    class Macro(DynamicBase):
        __tablename__ = tablename
        __table_args__ = {'extend_existing': True}

        id = Column(Integer(), primary_key=True, autoincrement=True)
        character_id = Column(Integer(), nullable=False)
        name = Column(String(), nullable=False, unique=False)
        macro = Column(String(), nullable=False, unique=False)

    logging.info(f"get_macro: returning macro")
    return Macro


async def get_macro_table(ctx, metadata, engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(Global).where(
            or_(
                Global.tracker_channel == ctx.interaction.channel_id,
                Global.gm_tracker_channel == ctx.interaction.channel_id
            )
        )
        )
        guild = result.scalars().one()

    table = MacroTable(ctx, metadata, guild.id).macro_table()
    return table


class MacroTable:
    def __init__(self, ctx, metadata, id):
        self.guild = ctx.interaction.guild_id
        self.channel = ctx.interaction.channel_id
        self.metadata = metadata
        self.id = id

    def macro_table(self):
        tablename = f"Macro_{self.id}"
        macro = db.Table(tablename, self.metadata,
                         db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                         db.Column('character_id', db.INTEGER(), ForeignKey(f'Tracker_{self.id}.id')),
                         db.Column('name', db.String(255), nullable=False, unique=False),
                         db.Column('macro', db.String(255), nullable=False, unique=False)
                         )
        return macro


def disease_table(metadata):
    tablename = f"disease"
    emp = db.Table(tablename, metadata,
                   db.Column('Type', db.Text()),
                   db.Column('ID', db.INTEGER(), primary_key=True, autoincrement=False),
                   db.Column('Title', db.String(255)),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp


def feat_table(metadata):
    tablename = f"feat"
    emp = db.Table(tablename, metadata,
                   db.Column('Type', db.Text()),
                   db.Column('ID', db.INTEGER(), primary_key=True, autoincrement=False),
                   db.Column('Title', db.String(255)),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp


def power_table(metadata):
    tablename = f"power"
    emp = db.Table(tablename, metadata,
                   db.Column('Type', db.Text()),
                   db.Column('ID', db.INTEGER(), primary_key=True, autoincrement=False),
                   db.Column('Title', db.String(255)),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp


def monster_table(metadata):
    tablename = f"monster"
    emp = db.Table(tablename, metadata,
                   db.Column('Type', db.Text()),
                   db.Column('ID', db.INTEGER(), primary_key=True, autoincrement=False),
                   db.Column('Title', db.String(255)),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp


def item_table(metadata):
    tablename = "item"
    emp = db.Table(tablename, metadata,
                   db.Column('Type', db.Text()),
                   db.Column('ID', db.INTEGER(), primary_key=True, autoincrement=False),
                   db.Column('Title', db.String(255)),
                   db.Column('Category', db.String(255)),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp


def ritual_table(metadata):
    tablename = "ritual"
    emp = db.Table(tablename, metadata,
                   db.Column('Type', db.Text()),
                   db.Column('ID', db.INTEGER(), primary_key=True, autoincrement=False),
                   db.Column('Title', db.String(255)),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp

# Global Class
class Reminder(Base):
    __tablename__ = "reminder_table"
    id = Column(Integer(), primary_key=True, autoincrement=True)
    user = Column(String())
    guild_id = Column(BigInteger())
    channel = Column(BigInteger(), nullable=False, unique=False)
    message = Column(String(), nullable=False)
    timestamp = Column(Integer(), nullable=False)

def reminder_table(metadata):
    tablename = f"reminder_table"
    emp = db.Table(tablename, metadata,
                   db.Column('id', db.INTEGER(), primary_key=True, autoincrement=True),
                   db.Column('user', db.String(255)),
                   db.Column('guild_id', db.BigInteger()),
                   db.Column('channel', db.BigInteger(), nullable=False, unique=False),
                   db.Column('message', db.String(), nullable=False),
                   db.Column('timestamp', db.INTEGER(), nullable=False)
                   )
    return emp

class NPC(Base):
    __tablename__ = 'npc_data'
    # Columns
    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(), unique=True)
    level = Column(Integer())
    creatureType = Column(String())
    alignment = Column(String())
    ac = Column(Integer())
    hp = Column(Integer())
    init = Column(String())
    fort = Column(Integer())
    reflex = Column(Integer())
    will = Column(Integer())
    dc = Column(Integer())
    macros = Column(String())