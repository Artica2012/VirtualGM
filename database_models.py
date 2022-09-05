from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy as db

import discord

Base = declarative_base()

class TrackerTable(Base):
    #name schema is Tracker_{guild_id}
    __abstract__ = True

    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String(255), nullable=False)
    init = Column(Integer, default=0)
    player = Column(Boolean, default=False)
    user = Column(Integer, nullable=False)
    guild = Column(Integer, nullable=False)

    def __repr__(self):
        return f"ID: {self.id}, Name: {self.name}"


class ConditionTable(Base):
    # name schema os Condition_{guild_id}
    __abstract__ = True
    __guild_id__ = ''


    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey(f"Tracker_{__guild_id__}.id"))  # Foreign Key
    condition = Column(String(255), nullable=False)
    duration = Column(Integer)
    beginning = Column(Boolean, default=False)

    # relationships
    tracker = relationship(f"Tracker_{__guild_id__}", backref=f"Condition_{__guild_id__}")


class Global(Base):
    __tablename__ = "global_manager"

    guild_id = Column(Integer(), primary_key=True, autoincrement=False)
    time = Column(Integer(), default=0, nullable=False)
    initiative = Column(Integer())

def get_guild_tracker(server: discord.Guild):
    guild_id = server.id
    tablename = f"{guild_id}"
    class_name = f"Tracker_{guild_id}"
    Model = type(class_name, (TrackerTable,),{'__tablename__':tablename, 'guild_id': guild_id })
    return Model

def get_guild_conditions(server:discord.Guild):
    guild_id = server.id
    tablename = f"{guild_id}"
    class_name = f"Condition_{guild_id}"
    Model = type(class_name, (ConditionTable,),{'__tablename__':tablename, 'guild_id': guild_id})
    return Model

