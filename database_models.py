from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy as db

import discord

Base = declarative_base()

class Global(Base):
    __tablename__ = "global_manager"

    guild_id = Column(Integer(), primary_key=True, autoincrement=False)
    time = Column(Integer(), default=0, nullable=False)
    initiative = Column(Integer())
    saved_order = Column(String())

