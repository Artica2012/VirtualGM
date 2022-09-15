from sqlalchemy import Column, ForeignKey
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, BigInteger
from sqlalchemy import String, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.event import listens_for
from sqlalchemy.orm import relationship
import sqlalchemy as db

import discord

import os
from dotenv import load_dotenv

# define global variables
from database_operations import get_db_engine

load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
USERNAME = os.getenv('Username')
PASSWORD = os.getenv('Password')
HOSTNAME = os.getenv('Hostname')
PORT = os.getenv('PGPort')

Base = declarative_base()


class Global(Base):
    __tablename__ = "global_manager"

    guild_id = Column(BigInteger(), primary_key=True, autoincrement=False)
    time = Column(BigInteger(), default=0, nullable=False)
    initiative = Column(Integer())
    saved_order = Column(String(), default='')
    gm = Column(String())
    tracker = Column(BigInteger(), nullable=True)
    tracker_channel = Column(BigInteger(), nullable=True)
    gm_tracker = Column(BigInteger(), nullable=True)
    gm_tracker_channel = Column(BigInteger(), nullable=True)

@listens_for(Global.initiative, "modified")
def receive_modified(target, initiator):
    print('Modified Global')


class TrackerTable():
    def __init__(self, server: discord.Guild, metadata):
        self.server = server
        self.metadata = metadata

    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    @listens_for(engine, 'after_cursor_execute')
    def flushed(self, session, flush_context, instances):
        print('Flushed')

    def tracker_table(self):
        tablename = f"Tracker_{self.server.id}"
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

class ConditionTable():
    def __init__(self, server: discord.Guild, metadata):
        self.server = server
        self.metadata = metadata

    def condition_table(self,):
        tablename = f"Condition_{self.server.id}"
        con = db.Table(tablename, self.metadata,
                       db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                       db.Column('character_id', db.INTEGER(), ForeignKey(f'Tracker_{self.server.id}.id')),
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
                   db.Column('Level', db.INTEGER, nullable=True),
                   db.Column('Source', db.String(255), nullable=True),
                   db.Column('Data', db.Text(), default=''),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp


def feat_table(metadata):
    tablename = f"feat"
    emp = db.Table(tablename, metadata,
                   db.Column('Type', db.Text()),
                   db.Column('ID', db.INTEGER(), primary_key=True, autoincrement=False),
                   db.Column('Title', db.String(255)),
                   db.Column('Tier', db.String(255), nullable=True),
                   db.Column('Source', db.String(255), nullable=True),
                   db.Column('Data', db.Text(), default=''),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp


def power_table(metadata):
    tablename = f"power"
    emp = db.Table(tablename, metadata,
                   db.Column('Type', db.Text()),
                   db.Column('ID', db.INTEGER(), primary_key=True, autoincrement=False),
                   db.Column('Title', db.String(255)),
                   db.Column('Level', db.INTEGER(), nullable=True),
                   db.Column('Action', db.String(255), nullable=True),
                   db.Column('Class', db.String(25), nullable=True),
                   db.Column('Source', db.String(255), nullable=True),
                   db.Column('Data', db.Text(), default=''),
                   db.Column('URL', db.String(255), default=''),
                   )
    return emp
