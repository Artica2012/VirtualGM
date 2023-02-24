import os
import logging

import discord
import sqlalchemy as db
from dotenv import load_dotenv
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer, BigInteger
from sqlalchemy import String, Boolean
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

class PF2_Character_Model:
    def __init__(self, ctx, metadata, id):
        self.guild = ctx.interaction.guild_id
        self.channel = ctx.interaction.channel_id
        self.metadata = metadata
        self.id = id

    def pf2_character_model_table(self):
        tablename= f"Tracker_{self.id}"

        emp = db.Table(
            tablename,
            self.metadata,
            db.Column("id", db.INTEGER(), autoincrement=True, primary_key=True),
            db.Column("name", db.String(255), nullable=False, unique=True),
            db.Column("player", db.BOOLEAN, default=False),
            db.Column("user", db.BigInteger(), nullable=False),
            db.Column("current_hp", db.INTEGER(), default=0),
            db.Column("max_hp", db.INTEGER(), default=1),
            db.Column("temp_hp", db.INTEGER(), default=0),
            db.Column("active", db.BOOLEAN, default=True),

            db.Column('char_class', db.String(255), nullable=False),
            db.Column("level", db.INTEGER(), nullable=False),
            db.Column("ac_base", db.INTEGER(), nullable=False),
            db.Column("class_dc", db.INTEGER(), nullable=False),

            db.Column("str", db.INTEGER(), nullable=False),
            db.Column("dex", db.INTEGER(), nullable=False),
            db.Column("con", db.INTEGER(), nullable=False),
            db.Column("itl", db.INTEGER(), nullable=False),
            db.Column("wis", db.INTEGER(), nullable=False),
            db.Column("cha", db.INTEGER(), nullable=False),

            db.Column("fort_prof", db.INTEGER(), nullable=False),
            db.Column("will_prof", db.INTEGER(), nullable=False),
            db.Column("reflex_prof", db.INTEGER(), nullable=False),

            db.Column("perception_prof", db.INTEGER(), nullable=False),
            db.Column("class_prof", db.INTEGER(), nullable=False),
            db.Column("key_ability", db.String(255), nullable=False),

            db.Column("unarmored_prof", db.INTEGER(), nullable=False),
            db.Column("light_armor_prof", db.INTEGER(), nullable=False),
            db.Column("medium_armor_prof", db.INTEGER(), nullable=False),
            db.Column("heavy_armor_prof", db.INTEGER(), nullable=False),

            db.Column("unarmed_prof", db.INTEGER(), nullable=False),
            db.Column("simple_prof", db.INTEGER(), nullable=False),
            db.Column("martial_prof", db.INTEGER(), nullable=False),
            db.Column("advanced_prof", db.INTEGER(), nullable=False),

            db.Column("arcane_prof", db.INTEGER(), nullable=False),
            db.Column("divine_prof", db.INTEGER(), nullable=False),
            db.Column("occult_prof", db.INTEGER(), nullable=False),
            db.Column("primal_prof", db.INTEGER(), nullable=False),

            db.Column("acrobatics_prof", db.INTEGER(), nullable=False),
            db.Column("arcana_prof", db.INTEGER(), nullable=False),
            db.Column("athletics_prof", db.INTEGER(), nullable=False),
            db.Column("crafting_prof", db.INTEGER(), nullable=False),
            db.Column("deception_prof", db.INTEGER(), nullable=False),
            db.Column("diplomacy_prof", db.INTEGER(), nullable=False),
            db.Column("class_dc", db.INTEGER(), nullable=False),
            db.Column("class_dc", db.INTEGER(), nullable=False),
            db.Column("class_dc", db.INTEGER(), nullable=False),
            db.Column("class_dc", db.INTEGER(), nullable=False),
            db.Column("class_dc", db.INTEGER(), nullable=False),
            db.Column("class_dc", db.INTEGER(), nullable=False),

        )

        acrobatics_prof = Column(Integer(), nullable=False)
        arcana_prof = Column(Integer(), nullable=False)
        athletics_prof = Column(Integer(), nullable=False)
        crafting_prof = Column(Integer(), nullable=False)
        deception_prof = Column(Integer(), nullable=False)
        diplomacy_prof = Column(Integer(), nullable=False)
        intimidation_prof = Column(Integer(), nullable=False)
        medicine_prof = Column(Integer(), nullable=False)
        nature_prof = Column(Integer(), nullable=False)
        occultism_prof = Column(Integer(), nullable=False)
        performance_prof = Column(Integer(), nullable=False)
        religion_prof = Column(Integer(), nullable=False)
        society_prof = Column(Integer(), nullable=False)
        stealth_prof = Column(Integer(), nullable=False)
        survival_prof = Column(Integer(), nullable=False)
        thievery_prof = Column(Integer(), nullable=False)

        # Plan to save parsable lists here
        lores = Column(String())
        feats = Column(String())

        # Calculated stats
        str_mod = Column(Integer())
        dex_mod = Column(Integer())
        con_mod = Column(Integer())
        itl_mod = Column(Integer())
        wis_mod = Column(Integer())
        cha_mod = Column(Integer())

        # Saves
        fort_mod = Column(Integer())
        will_mod = Column(Integer())
        reflex_mod = Column(Integer())

        acrobatics_mod = Column(Integer())
        arcana_mod = Column(Integer())
        athletics_mod = Column(Integer())
        crafting_mod = Column(Integer())
        deception_mod = Column(Integer())
        diplomacy_mod = Column(Integer())
        intimidation_mod = Column(Integer())
        medicine_mod = Column(Integer())
        nature_mod = Column(Integer())
        occultism_mod = Column(Integer())
        performance_mod = Column(Integer())
        religion_mod = Column(Integer())
        society_mod = Column(Integer())
        stealth_mod = Column(Integer())
        survival_mod = Column(Integer())
        thievery_mod = Column(Integer())

        arcane_mod = Column(Integer())
        divine_mod = Column(Integer())
        occult_mod = Column(Integer())
        primal_mod = Column(Integer())

        # unarmed_mod = Column(Integer())
        # simple_mod = Column(Integer())
        # martial_mod = Column(Integer())
        # advanced_mod = Column(Integer())

        ac_total = Column(Integer())
        resistance = Column(String())


    logging.info("get_tracker: returning tracker")
    return Tracker