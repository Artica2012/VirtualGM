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
        tablename = f"Tracker_{self.id}"

        emp = db.Table(
            tablename,
            self.metadata,
            db.Column("id", db.INTEGER(), autoincrement=True, primary_key=True),
            db.Column("name", db.String(255), nullable=False, unique=True),
            db.Column("init", db.INTEGER(), default=0),
            db.Column("player", db.BOOLEAN, default=False),
            db.Column("user", db.BigInteger(), nullable=False),
            db.Column("current_hp", db.INTEGER(), default=0),
            db.Column("max_hp", db.INTEGER(), default=1),
            db.Column("temp_hp", db.INTEGER(), default=0),
            db.Column("init_string", db.String(255), nullable=True),
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
            db.Column("intimidation_prof", db.INTEGER(), nullable=False),
            db.Column("medicine_prof", db.INTEGER(), nullable=False),
            db.Column("nature_prof", db.INTEGER(), nullable=False),
            db.Column("occultism_prof", db.INTEGER(), nullable=False),
            db.Column("performance_prof", db.INTEGER(), nullable=False),
            db.Column("religion_prof", db.INTEGER(), nullable=False),
            db.Column("society_prof", db.INTEGER(), nullable=False),
            db.Column("stealth_prof", db.INTEGER(), nullable=False),
            db.Column("survival_prof", db.INTEGER(), nullable=False),
            db.Column("thievery_prof", db.INTEGER(), nullable=False),

            db.Column('lores', db.String()),
            db.Column('feats', db.String()),

            db.Column("str_mod", db.INTEGER()),
            db.Column("dex_mod", db.INTEGER()),
            db.Column("con_mod", db.INTEGER()),
            db.Column("itl_mod", db.INTEGER()),
            db.Column("wis_mod", db.INTEGER()),
            db.Column("cha_mod", db.INTEGER()),

            db.Column("fort_mod", db.INTEGER()),
            db.Column("will_mod", db.INTEGER()),
            db.Column("reflex_mod", db.INTEGER()),

            db.Column("acrobatics_mod", db.INTEGER()),
            db.Column("arcana_mod", db.INTEGER()),
            db.Column("athletics_mod", db.INTEGER()),
            db.Column("crafting_mod", db.INTEGER()),
            db.Column("deception_mod", db.INTEGER()),
            db.Column("diplomacy_mod", db.INTEGER()),
            db.Column("intimidation_mod", db.INTEGER()),
            db.Column("medicine_mod", db.INTEGER()),
            db.Column("nature_mod", db.INTEGER()),
            db.Column("occultism_mod", db.INTEGER()),
            db.Column("performance_mod", db.INTEGER()),
            db.Column("religion_mod", db.INTEGER()),
            db.Column("society_mod", db.INTEGER()),
            db.Column("stealth_mod", db.INTEGER()),
            db.Column("survival_mod", db.INTEGER()),
            db.Column("thievery_mod", db.INTEGER()),

            db.Column("arcane_mod", db.INTEGER()),
            db.Column("divine_mod", db.INTEGER()),
            db.Column("occult_mod", db.INTEGER()),
            db.Column("primal_mod", db.INTEGER()),

            db.Column("ac_total", db.INTEGER()),
            db.Column("resistance", db.String()),
            db.Column("perception_mod", db.INTEGER()),
            db.Column("macros", db.String()),
            db.Column("attacks", db.JSON()),
            db.Column("spells", db.JSON())
        )

        logging.info("pf2_character_model_table")
        return emp


class EPF_ConditionTable:
    def __init__(self, ctx, metadata, id):
        self.metadata = metadata
        self.id = id

    def condition_table(
        self,
    ):
        tablename = f"Condition_{self.id}"
        con = db.Table(
            tablename,
            self.metadata,
            db.Column("id", db.INTEGER(), autoincrement=True, primary_key=True),
            db.Column("character_id", db.INTEGER(), ForeignKey(f"Tracker_{self.id}.id")),
            db.Column("counter", db.BOOLEAN(), default=False),
            db.Column("title", db.String(255), nullable=False),
            db.Column("number", db.INTEGER(), nullable=True, default=None),
            db.Column("auto_increment", db.BOOLEAN, nullable=False, default=False),
            db.Column("time", db.BOOLEAN, default=False),
            db.Column("visible", db.BOOLEAN, default=True),
            db.Column("flex", db.BOOLEAN, default=False),
            db.Column("action", db.String(), default="")
        )
        return con
