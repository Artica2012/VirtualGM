import json
import logging

import discord
from sqlalchemy import select, func

import Systems.EPF.EPF_Character
from Backend.Database.engine import async_session, lookup_session
from Systems.EPF.EPF_Automation_Data import EPF_retreive_complex_data
from Systems.EPF.EPF_Character import EPF_Weapon
from Backend.Database.database_models import get_EPF_tracker
from Backend.utils.utils import get_guild


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

        self.stats = {}

    async def read_file(self, attachment):
        file = await attachment.read()
        self.data = json.loads(file)
        # print(self.data)

    async def import_character(self):
        guild = await get_guild(self.ctx, None)
        EPF_Tracker = await get_EPF_tracker(self.ctx)

        output = await self.parse_char()

        async with async_session() as session:
            query = await session.execute(
                select(EPF_Tracker).where(func.lower(EPF_Tracker.name) == self.char_name.lower())
            )
            character = query.scalars().all()
        if len(character) > 0:
            overwrite = True
            await self.overwrite_character(output)
        else:
            overwrite = False
            await self.write_character(output)

        await Systems.EPF.EPF_Character.write_bonuses(self.ctx, guild, self.char_name, [])
        await Systems.EPF.EPF_Character.calculate(self.ctx, self.char_name, guild=guild)

        Character = await Systems.EPF.EPF_Character.get_EPF_Character(self.char_name, self.ctx, guild)
        # await Character.update()
        if not overwrite:
            if guild.initiative is not None:
                # print("In initiative")
                try:
                    await Character.roll_initiative()
                except Exception:
                    logging.error("Error Rolling Initiative")

        return True

    async def parse_char(self):
        output = {}
        output["level"] = self.data["character"]["level"]
        output["max_hp"] = self.data["stats"]["maxHP"]
        output["ac"] = self.data["stats"]["totalAC"]
        general_info = json.loads(self.data["stats"]["generalInfo"])
        output["class"] = general_info["className"]
        output["key_ability"] = self.data["character"]["_class"]["keyAbility"]

        # stats
        stats = {}
        ab_data = self.data["stats"]["totalAbilityScores"]
        parsed_ab_data = json.loads(ab_data)
        # print(parsed_ab_data)
        for item in parsed_ab_data:
            stats[item["Name"]] = item["Score"]
        output["stats"] = stats
        self.stats = stats

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
        skills["classDCProf"] = self.data["stats"]["classDCProfMod"]
        skills["Perception"] = self.data["stats"]["perceptionProfMod"]

        output["skills"] = skills
        lores = ""
        for key in output["skills"]:
            if "Lore" in key:
                string = f"{key}, {output['skills'][key]}; "
                lores += string
        output["lores"] = lores
        # print(lores)

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
        # print(feat_list)
        feats = ", ".join(feat_list)
        output["feats"] = feats

        weap_spec = None
        # weapon Specialization
        for item in self.data["metaData"]:
            if item["source"] == "weaponSpecialization":
                weap_spec = "spec"
            elif item["source"] == "greaterWeaponSpecialization":
                weap_spec = "greater"

        # Attacks
        weapons = {}
        # Parsing Inventory
        # print("Inventory")
        for item in self.data["invItems"]:
            if item["itemIsWeapon"] == 1:
                fundRuneID = {
                    None: ("", 1),
                    24: ("striking", 2),
                    29: ("greaterStriking", 3),
                    33: ("majorStriking", 4),
                }
                fundPotencyRuneID = {None: 0, 20: 1, 27: 2, 31: 3, 112: 4}

                weapon = {
                    "display": item["name"],  # Display Name
                    "prof": "unarmed",  # get from lookup,  # Proficiency (Unarmed, Simple, Martial, Advanced)
                    "die": item["itemWeaponDieType"],  # Damage Die Size
                    "pot": fundPotencyRuneID[item["fundPotencyRuneID"]],  # Potency Rune (1,2,3)
                    "str": fundRuneID[item["fundRuneID"]][0],
                    # "", striking, greaterStriking, majorStriking (Pathbuilder Legacy Purposes)
                    "name": item["_itemOriginalName"],  # Weapon Name (For lookup)
                    "runes": None,  # List of runes (For future use)
                    "die_num": fundRuneID[item["fundRuneID"]][1],  # Number of damage die
                    "crit": "*2",  # Crit string, defaults to *2, but could be *2+1d6 or something of the sort
                    "stat": "str",  # What stat to use for damage
                    "dmg_type": "Bludgeoning",  # Damage Type
                    "attk_stat": "str",  # What stat to use for the attack (probably str or dex)
                    "traits": [],
                    "mat": item["materialType"],
                }

                edited_attack = await self.attack_lookup(weapon)

                # Handle Weapon Specialization Bonus Damage
                dmg_bonus = 0
                # print(output['proficiencies'])
                # print(edited_attack['display'])
                # print(edited_attack['prof'])

                try:
                    prof_lvl = output["proficiencies"][edited_attack["prof"]]
                    # print(prof_lvl)
                except KeyError as e:
                    logging.error(f"Wanderer Prociency Error:, {e}")
                    prof_lvl = 0

                if weap_spec == "spec":
                    match prof_lvl:  # noqa
                        case 4:
                            dmg_bonus = 2
                        case 6:
                            dmg_bonus = 3
                        case 8:
                            dmg_bonus = 4
                if weap_spec == "greater":
                    match prof_lvl:  # noqa
                        case 4:
                            dmg_bonus = 4
                        case 6:
                            dmg_bonus = 6
                        case 8:
                            dmg_bonus = 8

                edited_attack["dmg_bonus"] = dmg_bonus
                # print(weapon)
                weapons[item["name"]] = edited_attack
        # print(weapons)

        for feat in feat_list:
            feat_data = await EPF_retreive_complex_data(feat)
            for x in feat_data:
                weapons[x.display_name] = x.data

        output["attacks"] = weapons

        spell_casting_classes = []
        for item in self.data["metaData"]:
            if (
                "PREPARED-BOOK" in item["value"]
                or "SPONTANEOUS-REPERTOIRE" in item["value"]
                or "PREPARED-LIST" in item["value"]
            ):
                sp_class = item["value"].split("=")[0]
                spell_casting_classes.append(sp_class)
                # print("spellcasting class", sp_class)

        # Spell Stuff
        traditions = ["ARCANE", "DIVINE", "PRIMAL", "OCCULT"]
        skills = ["CON", "INT", "WIS", "CHA"]

        sp_db = []
        for sp_class in spell_casting_classes:
            name = sp_class
            trad = None
            stat = None
            for item in self.data["metaData"]:
                if sp_class.upper() in item["value"]:
                    i = item["value"].split("=")[1]
                    if i in traditions:
                        trad = i
                    elif i in skills:
                        stat = i
            sp_data = {"name": name, "trad": trad, "stat": stat}
            sp_db.append(sp_data)

        spells = {}
        for spell in self.data["spellBookSpells"]:
            for sp_class in sp_db:
                if spell["spellSRC"].lower() == sp_class["name"].lower():
                    spells[spell["_spellName"]] = {"trad": sp_class["trad"], "stat": sp_class["stat"]}
        # print(spells)

        spell_library = {}
        for spell in self.data["spellBookSpells"]:
            for sp_class in sp_db:
                if spell["spellSRC"].lower() == sp_class["name"].lower():
                    spell_name = spell["_spellName"]
                    spell_data = await EPF_retreive_complex_data(spell_name)
                    if len(spell_data) > 0:
                        for s in spell_data:
                            data = s.data
                            data["ability"] = sp_class["stat"].lower()
                            data["trad"] = sp_class["trad"].lower()
                            spell_library[s.display_name] = data
                    else:
                        spell_data = await Systems.EPF.EPF_Character.spell_lookup(spell_name)
                        match sp_class["trad"]:  # noqa
                            case "ARCANE":
                                prof = output["proficiencies"]["arcaneprof"]
                            case "DIVINE":
                                prof = output["proficiencies"]["divineprof"]
                            case "PRIMAL":
                                prof = output["proficiencies"]["primalprof"]
                            case "OCCULT":
                                prof = output["proficiencies"]["occultprof"]
                            case _:
                                prof = 0

                        if spell_data[0] is True:
                            spell = {
                                "level": spell_data[1].level,
                                "tradition": sp_class["trad"].lower(),
                                "ability": sp_class["stat"].lower(),
                                "proficiency": prof,
                                "type": spell_data[1].type,
                                "save": spell_data[1].save,
                                "damage": spell_data[1].damage,
                                "heightening": spell_data[1].heightening,
                            }
                            spell_library[spell_name] = spell

        # print(spell_library)
        output["spells"] = spell_library

        return output

    async def write_character(self, output):
        EPF_Tracker = await get_EPF_tracker(self.ctx)

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
                    attacks=output["attacks"],
                    spells=output["spells"],
                    resistance={},
                    pic=self.image,
                )
                session.add(new_char)
            await session.commit()

    async def overwrite_character(self, output):
        EPF_Tracker = await get_EPF_tracker(self.ctx)

        async with async_session() as session:
            query = await session.execute(
                select(EPF_Tracker).where(func.lower(EPF_Tracker.name) == self.char_name.lower())
            )
            character = query.scalars().one()

            character.max_hp = output["max_hp"]
            character.char_class = output["class"]
            character.level = output["level"]
            character.ac_base = output["ac"]
            character.class_prof = output["skills"]["classDCProf"]
            character.class_dc = 0
            character.key_ability = output["key_ability"]

            character.str = output["stats"]["Strength"]
            character.dex = output["stats"]["Dexterity"]
            character.con = output["stats"]["Constitution"]
            character.itl = output["stats"]["Intelligence"]
            character.wis = output["stats"]["Wisdom"]
            character.cha = output["stats"]["Charisma"]

            character.fort_prof = output["saves"]["Fortitude"]
            character.reflex_prof = output["saves"]["Reflex"]
            character.will_prof = output["saves"]["Will"]

            character.unarmored_prof = 0
            character.light_armor_prof = 0
            character.medium_armor_prof = 0
            character.heavy_armor_prof = 0

            character.unarmed_prof = output["proficiencies"]["unarmed"]
            character.simple_prof = output["proficiencies"]["simple"]
            character.martial_prof = output["proficiencies"]["martial"]
            character.advanced_prof = output["proficiencies"]["advanced"]

            character.arcane_prof = output["proficiencies"]["arcaneprof"]
            character.divine_prof = output["proficiencies"]["divineprof"]
            character.occult_prof = output["proficiencies"]["occultprof"]
            character.primal_prof = output["proficiencies"]["primalprof"]

            character.acrobatics_prof = output["skills"]["Acrobatics"]
            character.arcana_prof = output["skills"]["Arcana"]
            character.athletics_prof = output["skills"]["Athletics"]
            character.crafting_prof = output["skills"]["Crafting"]
            character.deception_prof = output["skills"]["Deception"]
            character.diplomacy_prof = output["skills"]["Diplomacy"]
            character.intimidation_prof = output["skills"]["Intimidation"]
            character.medicine_prof = output["skills"]["Medicine"]
            character.nature_prof = output["skills"]["Nature"]
            character.occultism_prof = output["skills"]["Occultism"]
            character.perception_prof = output["skills"]["Perception"]
            character.performance_prof = output["skills"]["Performance"]
            character.religion_prof = output["skills"]["Religion"]
            character.society_prof = output["skills"]["Society"]
            character.stealth_prof = output["skills"]["Stealth"]
            character.survival_prof = output["skills"]["Survival"]
            character.thievery_prof = output["skills"]["Thievery"]

            character.lores = output["lores"]
            character.feats = output["feats"]
            character.attacks = output["attacks"]
            character.spells = output["spells"]
            if self.image is not None:
                character.pic = self.image

            await session.commit()

    async def attack_lookup(self, attack):
        # print(attack["display"])
        try:
            display_name = attack["display"].strip()
            async with lookup_session() as session:
                result = await session.execute(
                    select(EPF_Weapon).where(func.lower(EPF_Weapon.name) == display_name.lower())
                )
                data = result.scalars().one()
        except Exception:
            try:
                # print(attack["name"])
                item_name = attack["name"].strip()
                async with async_session() as session:
                    result = await session.execute(
                        select(EPF_Weapon).where(func.lower(EPF_Weapon.name) == item_name.lower())
                    )
                    data = result.scalars().one()
            except Exception:
                return attack
        # print(data.name, data.range, data.traits)

        if data.range is not None:
            if "thrown" in data.traits:
                attack["stat"] = "str"
                attack["attk_stat"] = "dex"
            else:
                attack["stat"] = None
                attack["attk_stat"] = "dex"
        # print(data.name)
        # print(data.traits)
        for item in data.traits:
            if "deadly" in item:
                if "deadly" in item:
                    string = item.split("-")
                    if data.striking_rune == "greaterStriking":
                        dd = 2
                    elif data.striking_rune == "majorStriking":
                        dd = 3
                    else:
                        dd = 1
                    attack["crit"] = f"*2 + {dd}{string[1]}"
            elif item.strip().lower() == "finesse":
                if self.stats != {}:
                    if self.stats["Dexterity"] > self.stats["Strength"]:
                        attack["attk_stat"] = "dex"
            elif item.strip().lower() == "brutal":
                attack["attk_stat"] = "str"
        attack["traits"] = data.traits
        attack["dmg_type"] = data.damage_type
        attack["prof"] = data.category.lower()
        # print(attack)
        return attack
