import json

import discord
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_operations import engine
from database_models import get_EPF_tracker


async def get_WandeerImporter(
    ctx: discord.ApplicationContext, char_name: str, attachment: discord.Attachment, image=None
):
    file = await attachment.read()
    data = json.loads(file)

    return WandererImporter(ctx, char_name, attachment, data, image)


class WandererImporter:
    def __init__(
        self, ctx: discord.ApplicationContext, char_name: str, file: discord.Attachment, data: dict, image=None
    ):
        self.ctx = ctx
        self.char_name = char_name
        self.file = file
        self.image = image
        self.data = data

    async def read_file(self, attachment):
        file = await attachment.read()
        self.data = json.loads(file)
        # print(self.data)

    async def import_character(self):
        self.parse_char()

    def parse_char(self):
        output = {}
        output["level"] = self.data["character"]["level"]
        output["max_hp"] = self.data["stats"]["maxHP"]
        output["ac"] = self.data["stats"]["totalAC"]
        general_info = json.loads(self.data["stats"]["generalInfo"])
        output["class"] = general_info["className"]
        output["key_ability"] = data["character"]["_class"]["keyAbility"]

        # stats
        stats = {}
        ab_data = self.data["stats"]["totalAbilityScores"]
        parsed_ab_data = json.loads(ab_data)
        print(parsed_ab_data)
        for item in parsed_ab_data:
            stats[item["Name"]] = item["Score"]
        output["stats"] = stats

        # Saves
        saves = {}
        save_data = self.data["stats"]["totalSaves"]
        parsed_save_data = json.loads(save_data)
        for item in parsed_save_data:
            saves[item["Name"]] = item["ProficiencyMod"]
        output["saves"] = saves

        # Skills
        skills = {}
        skill_data = self.data["stats"]["totalSkills"]
        parsed_skill_data = json.loads(skill_data)
        for item in parsed_skill_data:
            skills[item["Name"]] = item["ProficiencyMod"]
        skills["ClassDCProf"] = self.data["stats"]["classDCProfMod"]
        skills["Perception"] = self.data["stats"]["perceptionProfMod"]

        output["skills"] = skills
        lores = ""
        for key in output["skills"]:
            if "Lore" in key:
                string = f"{key}, {output['skills'][key]}; "
                lores += string
        output["lores"] = lores
        print(lores)

        proficiencies = {}
        proficiencies["arcaneprof"] = self.data["stats"]["arcaneSpellProfMod"]
        proficiencies["divineprof"] = self.data["stats"]["divineSpellProfMod"]
        proficiencies["occultprof"] = self.data["stats"]["occultSpellProfMod"]
        proficiencies["primalprof"] = self.data["stats"]["primalSpellProfMod"]
        proficiencies["unarmed"] = self.data["stats"]["unarmedProfMod"]
        proficiencies["simple"] = self.data["stats"]["simpleWeaponProfMod"]
        proficiencies["martial"] = self.data["stats"]["martialWeaponProfMod"]
        proficiencies["advanced"] = self.data["stats"]["advancedWeaponProfMod"]
        output["proficiencies"] = proficiencies

        # weapons

        output["weapon_data"] = json.loads(self.data["stats"]["weapons"])

        # feats
        feat_list = []
        feats = self.data["build"]["feats"]
        for item in feats:
            feat_list.append(item["value"]["name"])
        print(feat_list)
        feats = ", ".join(feat_list)
        output["feats"] = feats

        return output

    async def write_character(self, output):
        EPF_Tracker = await get_EPF_tracker(self.ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            async with session.begin():
                new_char = EPF_Tracker(
                    name=self.char_name,
                    player=True,
                    user=self.ctx.user.id,
                    current_hp=output["max_hp"],
                    max_hp=output["max_hp"],
                    temp_hp=0,
                    char_class=output["class"],
                    level=output["level"],
                    ac_base=output["ac"],
                    init=0,
                    class_prof=output["skills"]["classDCProf"],
                    class_dc=0,
                    str=output["stats"]["Strength"],
                    dex=output["stats"]["Dexterity"],
                    con=output["stats"]["Constitution"],
                    itl=output["stats"]["Intelligence"],
                    wis=output["stats"]["Wisdom"],
                    cha=output["stats"]["Charisma"],
                    fort_prof=output["saves"]["Fortitude"],
                    reflex_prof=output["saves"]["Reflex"],
                    will_prof=output["saves"]["Will"],
                    unarmored_prof=0,
                    light_armor_prof=0,
                    medium_armor_prof=0,
                    heavy_armor_prof=0,
                    unarmed_prof=output["proficiencies"]["unarmed"],
                    simple_prof=output["proficiencies"]["simple"],
                    martial_prof=output["proficiencies"]["martial"],
                    advanced_prof=output["proficiencies"]["advanced"],
                    arcane_prof=output["proficiencies"]["arcaneprof"],
                    divine_prof=output["proficiencies"]["divineprof"],
                    occult_prof=output["proficiencies"]["occultprof"],
                    primal_prof=output["proficiencies"]["primalprof"],
                    acrobatics_prof=output["skills"]["Acrobatics"],
                    arcana_prof=output["skills"]["Arcana"],
                    athletics_prof=output["skills"]["Athletics"],
                    crafting_prof=output["skills"]["Crafting"],
                    deception_prof=output["skills"]["Deception"],
                    diplomacy_prof=output["skills"]["Diplomacy"],
                    intimidation_prof=output["skills"]["Intimidation"],
                    medicine_prof=output["skills"]["Medicine"],
                    nature_prof=output["skills"]["Nature"],
                    occultism_prof=output["skills"]["Occultism"],
                    perception_prof=output["skills"]["Perception"],
                    performance_prof=output["skills"]["Performance"],
                    religion_prof=output["skills"]["Religion"],
                    society_prof=output["skills"]["Society"],
                    stealth_prof=output["skills"]["Stealth"],
                    survival_prof=output["skills"]["Survival"],
                    thievery_prof=output["skills"]["Thievery"],
                    lores=output["lores"],
                    feats=output["feats"],
                    key_ability=output["key_ability"],
                )
