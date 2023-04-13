import logging

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
        )

        logging.info("stf_character_model_table")
        return emp
