import logging

import d20
import sqlalchemy as db
from d20 import CritType

from Alt_Dice_Rollers import d20_to_d10


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
            db.Column("resistances", db.JSON()),
            db.Column("pic", db.String(), nullable=True),
        )

        logging.info("RED_character_model_table")
        return emp


class RED_Roll_Result:
    def __init__(self, roll_result: d20.RollResult):
        self.roll_result = d20_to_d10(roll_result)
        self._RED_crit_check()

    @property
    def crit(self) -> CritType:
        return self.roll_result.crit

    def _RED_crit_check(self):
        if self.crit == CritType.CRIT:
            additonal_dice = d20.roll("1d10")
            self.total = self.roll_result.total + additonal_dice.total
            self.output = f"{self.roll_result.result}\nPlus Critical dice: {additonal_dice.result}\nTotal: {self.total}"
        elif self.crit == CritType.FAIL:
            additonal_dice = d20.roll("1d10")
            self.total = self.roll_result.total - additonal_dice.total
            if self.total < 0:
                self.total = 0
            self.output = (
                f"{self.roll_result.result}\nMinus Critical dice: {additonal_dice.result}\nTotal: {self.total}"
            )
        else:
            self.total = self.roll_result.total
            self.output = self.roll_result.result

    def __str__(self):
        return self.output

    def __int__(self):
        return self.total

    def __float__(self):
        return self.total

    def __repr__(self):
        return f"<RED RollResult total={self.total}>"


def RED_eval_success(roll: RED_Roll_Result, goal: RED_Roll_Result):
    if roll.total > goal.total:
        return "Success"
    else:
        return "Failure"


RED_SS_DV = {
    "pistol": {6: 13, 12: 15, 25: 20, 50: 25, 100: 30, 200: 30, 400: None, 800: None},
    "smg": {6: 15, 12: 13, 25: 15, 50: 20, 100: 25, 200: 25, 400: 30, 800: None},
    "shotgun": {6: 13, 12: 15, 25: 20, 50: 25, 100: 30, 200: 35, 400: None, 800: None},
    "assault rifle": {6: 17, 12: 16, 25: 15, 50: 13, 100: 15, 200: 20, 400: 25, 800: 30},
    "sniper rifle": {6: 30, 12: 25, 25: 25, 50: 20, 100: 15, 200: 16, 400: 17, 800: 20},
    "bows and crossbow": {6: 15, 12: 13, 25: 15, 50: 17, 100: 20, 200: 22, 400: None, 800: None},
    "grenade launcher": {6: 16, 12: 15, 25: 15, 50: 17, 100: 20, 200: 22, 400: 25, 800: None},
    "rocket launcher": {6: 17, 12: 16, 25: 15, 50: 15, 100: 20, 200: 20, 400: 25, 800: 30},
}

RED_AF_DV = {
    "smg": {6: 15, 12: 13, 25: 15, 50: 20, 100: 25, 200: None, 400: None, 800: None},
    "assault rifle": {6: 17, 12: 16, 25: 15, 50: 13, 100: 15, 200: None, 400: None, 800: None},
}

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
