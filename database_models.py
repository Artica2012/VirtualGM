from sqlalchemy import Column, ForeignKey
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, BigInteger
from sqlalchemy import String, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy as db

import discord

Base = declarative_base()

class Global(Base):
    __tablename__ = "global_manager"

    guild_id = Column(BigInteger(), primary_key=True, autoincrement=False)
    time = Column(BigInteger(), default=0, nullable=False)
    initiative = Column(Integer())
    saved_order = Column(String(), default='')
    gm = Column(String())


def tracker_table(server: discord.Guild, metadata):
    tablename = f"Tracker_{server.id}"
    emp = db.Table(tablename, metadata,
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


def condition_table(server: discord.Guild, metadata):
    tablename = f"Condition_{server.id}"
    con = db.Table(tablename, metadata,
                   db.Column('id', db.INTEGER(), autoincrement=True, primary_key=True),
                   db.Column('character_id', db.INTEGER(), ForeignKey(f'Tracker_{server.id}.id')),
                   db.Column('condition', db.String(255), nullable=False),
                   db.Column('duration', db.INTEGER()),
                   db.Column('beginning', db.BOOLEAN, default=False)
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