import logging

import discord
import sqlalchemy as db
from sqlalchemy import ForeignKey


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
            db.Column("char_class", db.String(255), nullable=False),
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
            db.Column("lores", db.String()),
            db.Column("feats", db.String()),
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
            db.Column("resistance", db.JSON()),
            db.Column("perception_mod", db.INTEGER()),
            db.Column("macros", db.String()),
            db.Column("attacks", db.JSON()),
            db.Column("spells", db.JSON()),
            db.Column("bonuses", db.JSON()),
            db.Column("eidolon", db.BOOLEAN(), default=False),
            db.Column("partner", db.String(255)),
            db.Column("pic", db.String(), nullable=True),
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
            db.Column("action", db.String(), default=""),
            db.Column("target", db.INTEGER()),
            db.Column("stable", db.BOOLEAN(), default=False),
            db.Column("value", db.INTEGER()),
        )
        return con


# Conditions
EPF_Conditions = {
    "Blinded": "perception -4 s",
    "Clumsy": "dex -X s",
    "Confused": "ac -2 c",
    "Deafened": "perception -2 s",
    "Drained": "con -X s",
    "Dying": "prone, unconscious",
    "Enfeebled": "str -X s",
    "Fascinated": (
        "perception -2 s, acrobatics -2 s, arcana -2 s, athletics -2 s, crafting -2 s, deception -2 s, "
        "diplomacy -2 s, intimidation -2 s, medicine -2 s, nature -2 s, occultism -2 s, perception -2 s, "
        "performance -2 s, religion -2 s, society -2 s, stealth -2 s, survival -2 s, thievery -2 s"
    ),
    "Fatigued": "ac -1 s, fort -1 s, reflex -1 s, will -1 s",
    "Flat-Footed": "ac -2 c",
    "Frightened": (
        "perception -X s, acrobatics -X s, arcana -X s, athletics -X s, crafting -X s, deception -X s, "
        "diplomacy -X s, intimidation -X s, medicine -X s, nature -X s, occultism -X s, perception -X s, "
        "performance -X s, religion -X s, society -X s, stealth -X s, survival -X s, thievery -X s, ac -X s,"
        "fort -X s, reflex -X s, will -X s, attack -X s"
    ),
    "Paralyzed": "ac -2 c",
    "Prone": "ac -2 s, attack -2 c",
    "Sickened": "str -X s, dex -X s, con -X s, itl -X s, wis -X s, cha -X s, ac -X s",
    "Stupefied": "itl -X s, wis -X s, cha -X s",
    "Unconscious": "ac -4 s, perception -4 s, reflex -4 s",
    "Magic Weapon": "dmg_die +1 s, attack +1 s",
    "Shield Raised +1": "ac +1 c",
    "Shield Raised +2": "ac +2 c",
    "Shield Raised +3": "ac +3 c",
    "Inspire Courage": "attack +1 s, dmg +1 s",
    "Inspire Defense": "ac +1 s, fort +1 s, reflex +1 s, will +1 s",
    "Lesser Cover": "ac +1 c",
    "Standard Cover": "ac +2 c, reflex +2 c, stealth +2 c",
    "Greater Cover": "ac +4 c, reflex +4 c, stealth +4 c",
    "Exploration Avoid Notice": "init-skill stealth",
}

EPF_Stats = ["str", "dex", "con", "itl", "wis", "cha", "None"]

EPF_DMG_Types = [
    "Bludgeoning",
    "Piercing",
    "Slashing",
    "Acid",
    "Cold",
    "Electricity",
    "Fire",
    "Sonic",
    "Positive",
    "Negative",
    "Force",
    "Chaotic",
    "Evil",
    "Good",
    "Lawful",
    "Mental",
    "Poison",
    "Bleed",
    "Precision",
    "Cold Iron",
    "Orichalcum",
    "Silver",
    "All-Damage",
]

EPF_DMG_Types_Inclusive = [
    "Bludgeoning",
    "Piercing",
    "Slashing",
    "Acid",
    "Cold",
    "Electricity",
    "Fire",
    "Sonic",
    "Positive",
    "Negative",
    "Force",
    "Chaotic",
    "Evil",
    "Good",
    "Lawful",
    "Mental",
    "Poison",
    "Bleed",
    "Precision",
    "Cold Iron",
    "Orichalcum",
    "Silver",
    "All-Damage",
    "Critical-Hits",
    "Physical",
]

EPF_SKills = [
    "fortitude",
    "reflex",
    "will",
    "perception",
    "acrobatics",
    "arcana",
    "athletics",
    "crafting",
    "deception",
    "diplomacy",
    "intimidation",
    "lore",
    "medicine",
    "nature",
    "occultism",
    "performance",
    "religion",
    "society",
    "stealth",
    "survival",
    "thievery",
]

EPF_SKills_NO_SAVE = [
    "perception",
    "acrobatics",
    "arcana",
    "athletics",
    "crafting",
    "deception",
    "diplomacy",
    "intimidation",
    "medicine",
    "nature",
    "occultism",
    "performance",
    "religion",
    "society",
    "stealth",
    "survival",
    "thievery",
]

EPF_attributes = ["AC", "Fort", "Reflex", "Will", "DC"]


def EPF_Success_colors(success_string):
    if success_string == "Critical Success":
        return discord.Color.gold()
    elif success_string == "Success":
        return discord.Color.green()
    elif success_string == "Failure":
        return discord.Color.red()
    else:
        return discord.Color.dark_red()
