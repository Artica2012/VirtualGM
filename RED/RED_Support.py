import logging

import sqlalchemy as db


class RED_Character_Model:
    def __init__(self, ctx, metadata, id):
        self.guild = ctx.interaction.guild_id
        self.channel = ctx.interaction.channel_id
        self.metadata = metadata
        self.id = id

    def RED_character_model_table(self):
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
            db.Column("humanity", db.JSON(), nullable=False),
            db.Column("current_luck", db.INTEGER(), nullable=False),
            db.Column("stats", db.JSON(), nullable=False),
            db.Column("skills", db.JSON(), nullable=False),
            db.Column("attacks", db.JSON(), nullable=False),
            db.Column("armor", db.JSON(), nullable=False),
            db.Column("cyber", db.JSON(), nullable=False),
            db.Column("net", db.JSON(), nullable=False),
            db.Column("macros", db.JSON()),
            db.Column("bonuses", db.JSON()),
            db.Column("pic", db.String(), nullable=True),
        )

        logging.info("RED_character_model_table")
        return emp


# Conditions
RED_Conditions = {}

RED_Stats = []

RED_DMG_Types = []


RED_SKills = {
    "concentration": "will",
    "conceal / reveal object": "intel",
    "lip reading": "intel",
    "perception": "intel",
    "tracking": "intel",
    "athletics": "dex",
    "contortionist": "dex",
    "dance": "dex",
    "endurance": "will",
    "resist torture / drugs": "will",
    "stealth": "dex",
    "drive land vehicle": "ref",
    "pilot air vehicle": "ref",
    "pilot sea vehicle": "ref",
    "riding": "ref",
    "accounting": "intel",
    "animal handling": "intel",
    "bureaucracy": "intel",
    "business": "intel",
    "composition": "intel",
    "criminology": "intel",
    "cryptography": "intel",
    "deduction": "intel",
    "education": "intel",
    "library search": "intel",
    "tactics": "intel",
    "wilderness survival": "intel",
    "brawling": "dex",
    "evasion": "dex",
    "martial arts": "dex",
    "melee weapon": "dex",
    "acting": "cool",
    "archery": "ref",
    "autofire": "ref",
    "handgun": "ref",
    "heavy weapons": "ref",
    "shoulder arms": "ref",
    "bribery": "cool",
    "conversation": "emp",
    "human perception": "emp",
    "interrogation": "cool",
    "persuasion": "cool",
    "personal grooming": "cool",
    "streetwise": "cool",
    "trading": "cool",
    "wardrobe & style": "cool",
    "air vehicle tech": "tech",
    "basic tech": "tech",
    "cybertech": "tech",
    "demolitions": "tech",
    "electronics / security tech": "tech",
    "first aid": "tech",
    "forgery": "tech",
    "land vehicle tech": "tech",
    "paint / draw / sculpt": "tech",
    "paramedic": "tech",
    "photography / film": "tech",
    "pick lock": "tech",
    "pick pocket": "tech",
    "sea vehicle tech": "tech",
    "weaponstech": "tech",
}


RED_attributes = []
