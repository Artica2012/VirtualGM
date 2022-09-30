# database_models.py

from sqlalchemy import Column, ForeignKey
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, BigInteger
from sqlalchemy import String, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.event import listens_for
import sqlalchemy as db
from sqlalchemy.orm import Session
from sqlalchemy import union_all, and_, or_
from sqlalchemy import select, update, delete
import discord

import os
from dotenv import load_dotenv

# define global variables
from database_operations import get_db_engine

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

class Global(Base):
    __tablename__ = "global_manager"
    # ID Columns
    id = Column(Integer(), primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger())
    gm = Column(String())
    # Initiative Tracker
    initiative = Column(Integer())
    saved_order = Column(String(), default='')
    tracker = Column(BigInteger(), nullable=True)
    tracker_channel = Column(BigInteger(), nullable=True, unique=True)
    gm_tracker = Column(BigInteger(), nullable=True)
    gm_tracker_channel = Column(BigInteger(), nullable=True, unique=True)
    # Timekeeper Functionality
    timekeeping = Column(Boolean(), default=False)
    time = Column(BigInteger(), default=6, nullable=False)
    time_second = Column(Integer(), nullable=True)
    time_minute = Column(Integer(), nullable=True)
    time_hour = Column(Integer(), nullable=True)
    time_day = Column(Integer(), nullable=True)
    time_month = Column(Integer(), nullable=True)
    time_year = Column(Integer(), nullable=True)


class TrackerTable:
    def __init__(self, ctx: discord.ApplicationContext, metadata, engine):
        self.guild = ctx.guild.id
        self.channel = ctx.channel.id
        self.metadata = metadata
        with Session(engine) as session:
            guild = session.execute(select(Global).filter(
                    or_(
                        Global.tracker_channel == ctx.channel.id,
                        Global.gm_tracker_channel == ctx.channel.id
                    )
                )
            ).scalar_one()
            self.id = guild.id

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
                       )
        return emp


class ConditionTable:
    def __init__(self, ctx: discord.ApplicationContext, metadata, engine):
        self.guild = ctx.guild.id
        self.channel = ctx.channel.id
        self.metadata = metadata
        with Session(engine) as session:
            guild = session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.channel.id,
                        Global.gm_tracker_channel == ctx.channel.id
                    )
                )).scalar_one()
            self.id = guild.id

    def condition_table(self, ):
        tablename = f"Condition_{self.id}"
        con = db.Table(tablename, self.metadata,
                       db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                       db.Column('character_id', db.INTEGER(), ForeignKey(f'Tracker_{self.id}.id')),
                       db.Column('counter', db.BOOLEAN(), default=False),
                       db.Column('title', db.String(255), nullable=False),
                       db.Column('number', db.INTEGER(), nullable=True, default=None),
                       db.Column('auto_increment', db.BOOLEAN, nullable=False, default=False)
                       )
        return con


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