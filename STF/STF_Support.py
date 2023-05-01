import logging

import d20
import sqlalchemy as db


class STF_Character_Model:
    def __init__(self, ctx, metadata, id):
        self.guild = ctx.interaction.guild_id
        self.channel = ctx.interaction.channel_id
        self.metadata = metadata
        self.id = id

    def stf_character_model_table(self):
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
            db.Column("current_stamina", db.INTEGER(), default=0),
            db.Column("max_stamina", db.INTEGER(), default=1),
            db.Column("max_hp", db.INTEGER(), default=1),
            db.Column("temp_hp", db.INTEGER(), default=0),
            db.Column("init_string", db.String(255), nullable=True),
            db.Column("active", db.BOOLEAN, default=True),
            db.Column("level", db.INTEGER(), nullable=False),
            db.Column("base_eac", db.INTEGER(), nullable=False),
            db.Column("base_kac", db.INTEGER(), nullable=False),
            db.Column("bab", db.INTEGER(), nullable=False),
            db.Column("resolve", db.INTEGER(), default=1),
            db.Column("max_resolve", db.INTEGER(), default=1),
            db.Column("key_ability", db.String(255), default=""),
            db.Column("str", db.INTEGER(), nullable=False),
            db.Column("dex", db.INTEGER(), nullable=False),
            db.Column("con", db.INTEGER(), nullable=False),
            db.Column("itl", db.INTEGER(), nullable=False),
            db.Column("wis", db.INTEGER(), nullable=False),
            db.Column("cha", db.INTEGER(), nullable=False),
            db.Column("fort", db.INTEGER(), nullable=False),
            db.Column("will", db.INTEGER(), nullable=False),
            db.Column("reflex", db.INTEGER(), nullable=False),
            db.Column("acrobatics", db.INTEGER(), nullable=False),
            db.Column("athletics", db.INTEGER(), nullable=False),
            db.Column("bluff", db.INTEGER(), nullable=False),
            db.Column("computers", db.INTEGER(), nullable=False),
            db.Column("culture", db.INTEGER(), nullable=False),
            db.Column("diplomacy", db.INTEGER(), nullable=False),
            db.Column("disguise", db.INTEGER(), nullable=False),
            db.Column("engineering", db.INTEGER(), nullable=False),
            db.Column("intimidate", db.INTEGER(), nullable=False),
            db.Column("life_science", db.INTEGER(), nullable=False),
            db.Column("medicine", db.INTEGER(), nullable=False),
            db.Column("mysticism", db.INTEGER(), nullable=False),
            db.Column("perception", db.INTEGER(), nullable=False),
            db.Column("physical_science", db.INTEGER(), nullable=False),
            db.Column("piloting", db.INTEGER(), nullable=False),
            db.Column("sense_motive", db.INTEGER(), nullable=False),
            db.Column("sleight_of_hand", db.INTEGER(), nullable=False),
            db.Column("stealth", db.INTEGER(), nullable=False),
            db.Column("survival", db.INTEGER(), nullable=False),
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
            db.Column("athletics_mod", db.INTEGER()),
            db.Column("bluff_mod", db.INTEGER()),
            db.Column("computers_mod", db.INTEGER()),
            db.Column("culture_mod", db.INTEGER()),
            db.Column("diplomacy_mod", db.INTEGER()),
            db.Column("disguise_mod", db.INTEGER()),
            db.Column("engineering_mod", db.INTEGER()),
            db.Column("intimidate_mod", db.INTEGER()),
            db.Column("life_science_mod", db.INTEGER()),
            db.Column("medicine_mod", db.INTEGER()),
            db.Column("mysticism_mod", db.INTEGER()),
            db.Column("perception_mod", db.INTEGER()),
            db.Column("physical_science_mod", db.INTEGER()),
            db.Column("piloting_mod", db.INTEGER()),
            db.Column("sense_motive_mod", db.INTEGER()),
            db.Column("sleight_of_hand_mod", db.INTEGER()),
            db.Column("stealth_mod", db.INTEGER()),
            db.Column("survival_mod", db.INTEGER()),
            db.Column("eac", db.INTEGER()),
            db.Column("kac", db.INTEGER()),
            db.Column("macros", db.JSON()),
            db.Column("attacks", db.JSON()),
            db.Column("spells", db.JSON()),
            db.Column("bonuses", db.JSON()),
            db.Column("resistance", db.JSON()),
        )

        logging.info("stf_character_model_table")
        return emp


STF_Skills = [
    "Acrobatics",
    "Athletics",
    "Bluff",
    "Computers",
    "Culture",
    "Diplomacy",
    "Disguise",
    "Engineering",
    "Intimidate",
    "Life Science",
    "Medicine",
    "Mysticism",
    "Perception",
    "Physical Science",
    "Piloting",
    "Sense Motive",
    "Sleight of Hand",
    "Stealth",
    "Survival",
]

STF_DMG_Types = ["Acid", "Cold", "Electricity", "Fire", "Sonic", "Bludgeoning", "Piercing", "Slashing"]

STF_Saves = ["Fort", "Reflex", "Will"]
STF_Attributes = ["KAC", "EAC", "Fort", "Reflex", "Will", "DC"]
STF_Stats = ["str", "dex", "con", "itl", "wis", "cha", "None"]

STF_Conditions = {
    "Asleep": "perception -10 c",
    "Blinded": "acrobatics -4 a, athletics -4 a, piloting -4 a, sleight_of_hand -4 a, stealth -4 a, perception -4 a",
    "Dazzled": "attack -1 c, perception -1 c",
    "Deafened": "init -4 c, perception -4 c",
    "Entangled": (
        "kac -2 c, eac -2 c, attack -2 c, reflex -2 c, init -2 c, acrobatics -2 a, piloting -2 a, "
        "sleight_of_hand -2 a, stealth -2 a"
    ),
    "Flat Footed": "kac -2 c, eac -2 c",
    "Frightened": (
        "kac -2 c. eac -2 c, acrobatics -2 c, athletics -2 c, bluff -2 c, computers -2 c, culture -2 c, "
        "diplomacy -2 c, disguise -2 c, engineering -2 c, intimidate -2 c, life_science -2 c, medicine -2 c,"
        "mysticism -2 c, perception -2 c, physical_science -2 c, piloting -2 c, sense_motive -2 c, "
        "sleight_of-hand -2 c, stealth -2 c, survival -2 c, attack -2 c, fort -2 c, reflex -2 c, will -2 c"
    ),
    "Grappled": (
        "eac -2 c, kac -2 c, attack -2 c, reflex -2 c, init -2 c, acrobatics -4 a, piloting -4 a,"
        " sleight_of_hand -4 a, stealth -4 a, perception -4 a"
    ),
    "Off-Kilter": "kac -2 c, eac -2 c, attack -2 c",
    "Off-Target": "attack -2 c",
    "Panicked": (
        "acrobatics -2 c, athletics -2 c, bluff -2 c, computers -2 c, culture -2 c, "
        "diplomacy -2 c, disguise -2 c, engineering -2 c, intimidate -2 c, life_science -2 c, medicine -2 c,"
        "mysticism -2 c, perception -2 c, physical_science -2 c, piloting -2 c, sense_motive -2 c, "
        "sleight_of-hand -2 c, stealth -2 c, survival -2 c, attack -2 c, fort -2 c, reflex -2 c, will -2 c"
    ),
    "Paralyzed": "dex -5 c, acrobatics -5 a, piloting -5 a, sleight_of_hand -5 a, stealth -5 a",
    "Pinned": (
        "eac -4 c, kac -4 c, attack -4 c, reflex -4 c, init -4 c, acrobatics -4 a, piloting -4 a,"
        " sleight_of_hand -4 a, stealth -4 a"
    ),
    "Shaken": (
        "acrobatics -2 c, athletics -2 c, bluff -2 c, computers -2 c, culture -2 c, "
        "diplomacy -2 c, disguise -2 c, engineering -2 c, intimidate -2 c, life_science -2 c, medicine -2 c,"
        "mysticism -2 c, perception -2 c, physical_science -2 c, piloting -2 c, sense_motive -2 c, "
        "sleight_of-hand -2 c, stealth -2 c, survival -2 c, attack -2 c, fort -2 c, reflex -2 c, will -2 c"
    ),
    "Sickened": (
        "acrobatics -2 c, athletics -2 c, bluff -2 c, computers -2 c, culture -2 c, "
        "diplomacy -2 c, disguise -2 c, engineering -2 c, intimidate -2 c, life_science -2 c, medicine -2 c,"
        "mysticism -2 c, perception -2 c, physical_science -2 c, piloting -2 c, sense_motive -2 c, "
        "sleight_of-hand -2 c, stealth -2 c, survival -2 c, attack -2 c, fort -2 c, reflex -2 c, will -2 c"
        "eac -2 c, kac -2 c, attack -2 c, dmg -2 c"
    ),
}


def STF_eval_success(dice_result: d20.RollResult, goal: d20.RollResult):
    success_string = ""
    match dice_result.crit:  # noqa
        case d20.CritType.CRIT:
            success_string = "Success"
        case d20.CritType.FAIL:
            success_string = "Failure"
        case _:
            success_string = "Success" if dice_result.total >= goal.total else "Failure"

    return success_string
