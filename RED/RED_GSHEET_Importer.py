import logging
from math import floor

import d20
import discord
import numpy
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from EPF.EPF_Character import spell_lookup, EPF_Weapon, delete_intested_items, invest_items, get_EPF_Character
from database_models import get_EPF_tracker, get_RED_tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA, DATABASE
from EPF.EPF_NPC_Importer import write_resitances

Interpreter = {
    "U": 0,
    "T": 2,
    "E": 4,
    "M": 6,
    "L": 8,
    "Str": "str",
    "Dex": "dex",
    "Con": "con",
    "Int": "itl",
    "Wis": "wis",
    "Cha": "cha",
    "None": "",
    "Striking": "striking",
    "Greater Striking": "greaterStriking",
    "Major Striking": "majorStriking",
    "Yes": True,
    "No": False,
    numpy.nan: "",
}


async def red_g_sheet_import(
    ctx: discord.ApplicationContext, char_name: str, base_url: str, engine=None, guild=None, image=None
):
    try:
        parsed_url = base_url.split("/")
        # print(parsed_url)
        sheet_id = parsed_url[5]
        logging.warning(f"G-sheet import: ID - {sheet_id}")
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        df = pd.read_csv(url, header=[0])

        guild = await get_guild(ctx, guild)
        if engine == None:
            engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

        red_tracker = await get_RED_tracker(ctx, engine, id=guild.id)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            query = await session.execute(select(red_tracker).where(func.lower(red_tracker.name) == char_name.lower()))
            character = query.scalars().all()
        if len(character) > 0:
            overwrite = True
        else:
            overwrite = False
        headers = list(df.columns.values)
        # print(headers)
        # print(headers[0])
        # print(df)

        decision_header = headers[0].strip()

        if decision_header == "CyberpunkRED:":
            (character,) = await red_g_sheet_character_import(ctx, char_name, df, engine, guild)
        else:
            return False

        initiative_num = 0
        if not overwrite:
            if guild.initiative is not None:
                # print("In initiative")
                try:
                    perception_mod = character["level"] + character["perception"] + floor((character["wis"] - 10) / 2)
                    roll = d20.roll(f"1d20+{perception_mod}")
                    initiative_num = roll.total
                except Exception:
                    initiative_num = 0

        if "lore" in character.keys():
            print("lore")
            lore = character["lore"]
            print(lore)
        else:
            print("not lore")
            lore = ""

        if overwrite:
            async with async_session() as session:
                query = await session.execute(
                    select(red_tracker).where(func.lower(red_tracker.name) == char_name.lower())
                )
                character_data = query.scalars().one()

                character_data.max_hp = character["hp"]
                character_data.char_class = character["class"]
                character_data.ac_base = character["ac_base"]
                character_data.level = character["level"]
                character_data.class_dc = character["class_dc"]
                character_data.str = character["str"]
                character_data.dex = character["dex"]
                character_data.con = character["con"]
                character_data.itl = character["itl"]
                character_data.wis = character["wis"]
                character_data.cha = character["cha"]
                character_data.fort_pof = character["fort"]
                character_data.reflex_prof = character["reflex"]
                character_data.will_prof = character["will"]
                character_data.perception_prof = character["perception"]
                character_data.class_prof = character["class_prof"]
                character_data.key_ability = character["key_ability"]
                character_data.unarmored_prof = character["unarmored"]
                character_data.light_armor_prof = character["light"]
                character_data.medium_armor_prof = character["medium"]
                character_data.heavy_armor_prof = character["heavy"]

                character_data.unarmed_prof = character["unarmed"]
                character_data.simple_prof = character["simple"]
                character_data.martial_prof = character["martial"]
                character_data.advanced_prof = character["advanced"]

                character_data.arcane_prof = character["arcane"]
                character_data.divine_prof = character["divine"]
                character_data.occult_prof = character["occult"]
                character_data.primal_prof = character["primal"]

                character_data.acrobatics_prof = character["acrobatics"]
                character_data.arcana_prof = character["arcana"]
                character_data.athletics_prof = character["athletics"]
                character_data.crafting_prof = character["crafting"]
                character_data.deception_prof = character["deception"]
                character_data.diplomacy_prof = character["diplomacy"]
                character_data.intimidation_prof = character["intimidation"]
                character_data.medicine_prof = character["medicine"]
                character_data.nature_prof = character["nature"]
                character_data.occultism_prof = character["occultism"]
                character_data.performance_prof = character["performance"]
                character_data.religion_prof = character["religion"]
                character_data.society_prof = character["society"]
                character_data.stealth_prof = character["stealth"]
                character_data.survival_prof = character["survival"]
                character_data.thievery_prof = character["thievery"]
                character_data.feats = character["feats"]
                # character_data.spells = spells
                # character_data.attacks = attacks
                character_data.lores = lore
                if image is not None:
                    character.pic = image

                await session.commit()

        else:
            async with async_session() as session:
                async with session.begin():
                    new_char = red_tracker(
                        name=char_name,
                        player=True if "npc" not in character.keys() else False,
                        active=character["active"],
                        user=ctx.user.id,
                        current_hp=character["hp"],
                        max_hp=character["hp"],
                        temp_hp=0,
                        char_class=character["class"],
                        level=character["level"],
                        ac_base=character["ac_base"],
                        init=initiative_num,
                        class_prof=character["class_prof"],
                        class_dc=character["class_dc"],
                        str=character["str"],
                        dex=character["dex"],
                        con=character["con"],
                        itl=character["itl"],
                        wis=character["wis"],
                        cha=character["cha"],
                        fort_prof=character["fort"],
                        reflex_prof=character["reflex"],
                        will_prof=character["will"],
                        unarmored_prof=character["unarmored"],
                        light_armor_prof=character["light"],
                        medium_armor_prof=character["medium"],
                        heavy_armor_prof=character["heavy"],
                        unarmed_prof=character["unarmed"],
                        simple_prof=character["simple"],
                        martial_prof=character["martial"],
                        advanced_prof=character["advanced"],
                        arcane_prof=character["arcane"],
                        divine_prof=character["divine"],
                        occult_prof=character["occult"],
                        primal_prof=character["primal"],
                        acrobatics_prof=character["acrobatics"],
                        arcana_prof=character["arcana"],
                        athletics_prof=character["athletics"],
                        crafting_prof=character["crafting"],
                        deception_prof=character["deception"],
                        diplomacy_prof=character["diplomacy"],
                        intimidation_prof=character["intimidation"],
                        medicine_prof=character["medicine"],
                        nature_prof=character["nature"],
                        occultism_prof=character["occultism"],
                        perception_prof=character["perception"],
                        performance_prof=character["performance"],
                        religion_prof=character["religion"],
                        society_prof=character["society"],
                        stealth_prof=character["stealth"],
                        survival_prof=character["survival"],
                        thievery_prof=character["thievery"],
                        lores=lore,
                        feats=character["feats"],
                        key_ability=character["key_ability"],
                        # attacks=attacks,
                        # spells=spells,
                        # resistance=resistance,
                        eidolon=character["eidolon"],
                        partner=character["partner"],
                        pic=image,
                    )
                    session.add(new_char)
                await session.commit()

        Character = await get_EPF_Character(char_name, ctx, guild, engine)
        # Write the conditions
        # await write_resitances(resistance, Character, ctx, guild, engine)
        await Character.update()
        return True

    except Exception:
        logging.warning("epf_g_sheet_import")
        return False


async def red_g_sheet_character_import(ctx: discord.ApplicationContext, char_name: str, df, engine, guild):
    logging.info("g-sheet-char")
    try:
        df.rename(
            columns={
                "CyberpunkRED:": "a",
                "CyberpunkRED: ": "a",
                "Unnamed: 1": "b",
                "Unnamed: 2": "c",
                "Unnamed: 3": "d",
                "Unnamed: 4": "e",
                "Unnamed: 5": "f",
                "Unnamed: 6": "g",
                "Unnamed: 7": "h",
            },
            inplace=True,
        )

    except Exception:
        return False

    character = {
        "name": df.b[0],
        "level": int(df.d[0]),
        "active": True,
        "role": df.b[1],
        "hp": df.d[1],
    }
    stats = {}

    for i in range(2, 8):
        try:
            title = str(df.a[i])
            title = title.split(" ")[0].lower()
            base = int(df.b[i])
            stats[title] = {"value": base, "base": base}
        except Exception:
            pass
        try:
            title = str(df.c[i])
            title = title.split(" ")[0].lower()
            base = int(df.d[i])
            stats[title] = {"value": base, "base": base}
        except Exception:
            pass

    print(stats)
    character["stats"] = stats

    skills = {}

    feats = ""
    if character["UI"] == True:
        feats += "Untrained Improvisation, "
    character["feats"] = feats
    spells = {}
    attacks = {}
    items = []
    resistances = {"resist": {}, "weak": {}, "immune": {}}

    lore = ""
    for i in range(26, 30):
        print(df.d[i])
        if type(df.e[i]) == str and type(df.d[i]) == str:
            string = f"{df.d[i]}, {Interpreter[df.e[i]]}; "
            lore += string
    character["lore"] = lore

    for i in range(31, (len(df.a) - 1)):
        name = df.a[i]
        # print(name)
        if name != numpy.nan:
            lookup_data = await spell_lookup(name)
            if lookup_data[0] is True:
                tradition = df.c[i]
                # print(tradition)
                match tradition:  # noqa
                    case "Arcane":
                        ability = Interpreter[df.f[19]]
                        proficiency = Interpreter[df.e[19]]
                    case "Divine":
                        ability = Interpreter[df.f[20]]
                        proficiency = Interpreter[df.e[20]]
                    case "Occult":
                        ability = Interpreter[df.f[21]]
                        proficiency = Interpreter[df.e[21]]
                    case "Primal":
                        ability = Interpreter[df.f[22]]
                        proficiency = Interpreter[df.e[22]]
                    case _:
                        ability = "cha"
                        proficiency = 0

                spell = {
                    "level": int(df.b[i]),
                    "tradition": tradition,
                    "ability": ability,
                    "proficiency": proficiency,
                    "type": lookup_data[1].type,
                    "save": lookup_data[1].save,
                    "damage": lookup_data[1].damage,
                    "heightening": lookup_data[1].heightening,
                }
                spells[name] = spell

    for i in range(31, (len(df.e) - 1)):
        if df.e[i] == "Name" and df.f[i] is not numpy.nan:
            print(df.e[i])
            try:
                # print(df.f[i])
                try:
                    potency = int(df.f[i + 3])
                except Exception:
                    potency = 0
                die_num = 1
                # print(type(df.f[i + 4]))
                # print(df.f[i + 4])
                if Interpreter[df.f[i + 4]] == "striking":
                    die_num = 2
                elif Interpreter[df.f[i + 4]] == "greaterStriking":
                    die_num = 3
                elif Interpreter[df.f[i + 4]] == "majorStriking":
                    die_num = 4
                if df.f[i + 8] is not numpy.nan:
                    parsed_traits = df.f[i + 8].split(",")
                else:
                    parsed_traits = []
                if type(df.f[i + 9]) == str:
                    dmg_type = df.f[i + 9]
                else:
                    dmg_type = "Bludgeoning"

                attack_data = {
                    "display": df.f[i],
                    "name": df.f[i + 1],
                    "prof": df.f[i + 2].lower(),
                    "pot": potency,
                    "str": Interpreter[df.f[i + 4]],
                    "runes": [],
                    "die_num": die_num,
                    "die": df.f[i + 5],
                    "crit": "*2",
                    "stat": Interpreter[df.f[i + 7]],
                    "dmg_type": dmg_type,
                    "attk_stat": Interpreter[df.f[i + 6]],
                    "traits": parsed_traits,
                }
                edited_attack = await attack_lookup(attack_data, character)

                double_attacks = False
                # Check for two handed and fatal
                for trait in edited_attack["traits"]:
                    print(trait)
                    if "fatal-aim" in trait:
                        double_attacks = True
                        parsed_trait = trait.split("-")
                        fatal_die = parsed_trait[2]
                        attack_one = edited_attack.copy()
                        attack_two = edited_attack.copy()
                        trait_list = attack_one["traits"]
                        trait_copy = trait_list.copy()
                        for x, i in enumerate(trait_list):
                            if i == trait:
                                trait_copy[x] = f"fatal-{fatal_die}"

                        attack_one["traits"] = trait_copy
                        attack_one["display"] = f"{edited_attack['display']} (2H)"

                        trait_copy = []
                        for i in trait_list:
                            if i != trait:
                                trait_copy.append(i)

                        attack_two["display"] = f"{edited_attack['display']} (1H)"
                        attack_two["traits"] = trait_copy
                    if "two-hand" in trait:
                        double_attacks = True
                        parsed_trait = trait.split("-")
                        attk_2_die = parsed_trait[2]
                        attack_one = edited_attack.copy()
                        attack_two = edited_attack.copy()
                        attack_one["display"] = f"{edited_attack['display']} (2H)"
                        attack_one["die"] = attk_2_die
                        attack_two["display"] = f"{edited_attack['display']} (1H)"

                if double_attacks:
                    attacks[attack_one["display"]] = attack_one
                    attacks[attack_two["display"]] = attack_two
                else:
                    attacks[edited_attack["display"]] = edited_attack

            except Exception:
                pass
    # print(attacks)

    # print("Getting Items")
    for i in range(31, (len(df.h) - 1)):
        # print(i)
        # print(df.h[i])
        if df.h[i] != numpy.nan:
            # print(df.h[i])
            items.append(df.h[i])

    return character, spells, attacks, items, resistances


async def gs_npc_skill_calc(skill_mod, level, stat_mod):
    if skill_mod is numpy.nan:
        return 0
    else:
        return int(skill_mod) - level - stat_mod
