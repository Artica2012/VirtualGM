from math import floor

import d20
import discord
import numpy
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from EPF.EPF_Character import spell_lookup, EPF_Weapon, delete_intested_items, invest_items, get_EPF_Character
from database_models import get_EPF_tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA, DATABASE

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


async def epf_g_sheet_import(ctx: discord.ApplicationContext, char_name: str, base_url: str, engine=None, guild=None):
    try:
        # SHEET_ID = "1WKZ5xER17XHLjaj1uVtSdG60fapzxHnou8ic9bu3JHE"
        # https://docs.google.com/spreadsheets/d/1WKZ5xER17XHLjaj1uVtSdG60fapzxHnou8ic9bu3JHE/edit?usp=sharing
        parsed_url = base_url.split("/")
        print(parsed_url)
        sheet_id = parsed_url[5]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        df = pd.read_csv(url)
        df.rename(
            columns={
                "Info:": "a",
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

        # print(df)
    except Exception:
        return False

    guild = await get_guild(ctx, guild)
    if engine == None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    EPF_tracker = await get_EPF_tracker(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        query = await session.execute(select(EPF_tracker).where(EPF_tracker.name == char_name))
        character = query.scalars().all()
    if len(character) > 0:
        overwrite = True
    else:
        overwrite = False

    # for i in range(0, len(df.a)-1):
    #     print(df.iloc[[i]])

    character = {
        "name": df.b[0],
        "level": int(df.d[0]),
        "class": df.b[1],
        "hp": int(df.d[1]),
        "str": int(df.b[2]),
        "dex": int(df.b[3]),
        "con": int(df.b[4]),
        "itl": int(df.d[2]),
        "wis": int(df.d[3]),
        "cha": int(df.d[4]),
        "class_dc": int(df.b[5]),
        "ac_base": int(df.d[5]),
        "key_ability": Interpreter[df.f[5]],
        "fort": Interpreter[df.b[7]],
        "reflex": Interpreter[df.b[8]],
        "will": Interpreter[df.b[9]],
        "perception": Interpreter[df.b[11]],
        "acrobatics": Interpreter[df.b[13]],
        "arcana": Interpreter[df.b[14]],
        "athletics": Interpreter[df.b[15]],
        "crafting": Interpreter[df.b[16]],
        "deception": Interpreter[df.b[17]],
        "diplomacy": Interpreter[df.b[18]],
        "intimidation": Interpreter[df.b[19]],
        "medicine": Interpreter[df.b[20]],
        "nature": Interpreter[df.b[21]],
        "occultism": Interpreter[df.b[22]],
        "performance": Interpreter[df.b[23]],
        "religion": Interpreter[df.b[24]],
        "society": Interpreter[df.b[25]],
        "stealth": Interpreter[df.b[26]],
        "survival": Interpreter[df.b[27]],
        "thievery": Interpreter[df.b[28]],
        "UI": Interpreter[df.b[29]],
        "unarmored": Interpreter[df.e[7]],
        "light": Interpreter[df.e[8]],
        "medium": Interpreter[df.e[9]],
        "heavy": Interpreter[df.e[10]],
        "unarmed": Interpreter[df.e[13]],
        "simple": Interpreter[df.e[14]],
        "martial": Interpreter[df.e[15]],
        "advanced": Interpreter[df.e[16]],
        "arcane": Interpreter[df.e[19]],
        "divine": Interpreter[df.e[20]],
        "occult": Interpreter[df.e[21]],
        "primal": Interpreter[df.e[22]],
    }
    character["class_prof"] = (
        int(character["class_dc"])
        - int(character["level"])
        - (floor(int(character[character["key_ability"]]) - 10) / 2)
    )
    feats = ""
    if character["UI"] == True:
        feats += "Untrained Improvisation, "
    spells = {}
    attacks = {}
    items = []

    for i in range(31, (len(df.a) - 1)):
        name = df.a[i]
        print(name)
        if name != numpy.nan:
            lookup_data = await spell_lookup(name)
            if lookup_data[0] is True:
                tradition = df.c[i]
                print(tradition)
                match tradition:
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
        if df.e[i] == "Name" and df.f[i] != numpy.nan:
            try:
                print(df.f[i])
                try:
                    potency = int(df.f[i + 3])
                except Exception:
                    potency = 0
                die_num = 1
                print(type(df.f[i + 4]))
                print(df.f[i + 4])
                if Interpreter[df.f[i + 4]] == "striking":
                    die_num = 2
                elif Interpreter[df.f[i + 4]] == "greaterStriking":
                    die_num = 3
                elif Interpreter[df.f[i + 4]] == "majorStriking":
                    die_num = 4
                attack_data = {
                    "display_name": df.f[i],
                    "name": df.f[i + 1],
                    "prof": df.f[i + 2].lower(),
                    "pot": potency,
                    "str": Interpreter[df.f[i + 4]],
                    "runes": [],
                    "die_num": die_num,
                    "die": df.f[i + 5],
                    "crit": "*2",
                    "stat": Interpreter[df.f[i + 7]],
                    "dmg_type": "Bludgeoning",
                    "attk_stat": Interpreter[df.f[i + 6]],
                }
                edited_attack = await attack_lookup(attack_data, character)
                attacks[edited_attack["display_name"]] = edited_attack
            except Exception:
                pass
    print(attacks)

    print("Getting Items")
    for i in range(31, (len(df.h) - 1)):
        print(i)
        print(df.h[i])
        if df.h[i] != numpy.nan:
            print(df.h[i])
            items.append(df.h[i])

    initiative_num = 0
    if not overwrite:
        if guild.initiative is not None:
            print("In initiative")
            try:
                perception_mod = character["level"] + character["perception"] + floor((character["wis"] - 10) / 2)
                roll = d20.roll(f"1d20+{perception_mod}")
                initiative_num = roll.total
            except Exception:
                initiative_num = 0

    if overwrite:
        async with async_session() as session:
            query = await session.execute(select(EPF_tracker).where(EPF_tracker.name == char_name))
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
            character_data.feats = feats
            character_data.spells = spells
            character_data.attacks = attacks

            await session.commit()

    else:
        async with async_session() as session:
            async with session.begin():
                new_char = EPF_tracker(
                    name=char_name,
                    player=True,
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
                    lores="",
                    feats=feats,
                    key_ability=character["key_ability"],
                    attacks=attacks,
                    spells=spells,
                    resistance={"resist": {}, "weak": {}, "immune": {}},
                )
                session.add(new_char)
            await session.commit()

    await delete_intested_items(char_name, ctx, guild, engine)
    print(f"Items: {items}")
    for item in items:
        print(item)
        result = await invest_items(item, char_name, ctx, guild, engine)
        print(result)

    Character = await get_EPF_Character(char_name, ctx, guild, engine)
    await Character.update()
    return True


async def attack_lookup(attack, character: dict):
    lookup_engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    async_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(
                select(EPF_Weapon).where(func.lower(EPF_Weapon.name) == str(attack["display"]).lower())
            )
            data = result.scalars().one()
    except Exception:
        async with async_session() as session:
            result = await session.execute(
                select(EPF_Weapon).where(func.lower(EPF_Weapon.name) == str(attack["name"]).lower())
            )
            data = result.scalars().one()
    await lookup_engine.dispose()

    if data.range is not None:
        attack["stat"] = None
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
        elif item.strip().lower() == "finesse" and character["dex"] > character["str"]:
            # print("Finesse")
            attack["attk_stat"] = "dex"
        elif item.strip().lower() == "brutal":
            attack["attk_stat"] = "str"
    attack["traits"] = data.traits
    attack["dmg_type"] = data.damage_type
    return attack