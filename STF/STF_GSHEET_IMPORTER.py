import logging
from math import floor

import d20
import discord
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from STF.STF_Character import get_STF_Character
from database_models import get_STF_tracker
from database_operations import get_asyncio_db_engine
from utils.parsing import ParseModifiers
from utils.utils import get_guild
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA

Interpreter = {"str": "str", "dex": "dex", "con": "con", "int": "itl", "wis": "wis", "cha": "cha"}


def interpret(item):
    try:
        return Interpreter[item]
    except KeyError:
        return ""


async def stf_g_sheet_import(ctx: discord.ApplicationContext, char_name: str, base_url: str, engine=None, guild=None):
    # try:
    parsed_url = base_url.split("/")
    sheet_id = parsed_url[5]
    logging.warning(f"G-sheet import: ID - {sheet_id}")
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    print(url)
    df = pd.read_csv(url, header=[0])
    print(df)
    guild = await get_guild(ctx, guild)
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    STF_tracker = await get_STF_tracker(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        query = await session.execute(select(STF_tracker).where(func.lower(STF_tracker.name) == char_name.lower()))
        character = query.scalars().all()
    if len(character) > 0:
        overwrite = True
    else:
        overwrite = False
    headers = list(df.columns.values)
    print(headers)
    print(df)
    decision_header = headers[0].strip()

    if decision_header == "Starfinder Character Sheet:":
        character, spells, attacks, items, resistance = await stf_g_sheet_character_import(
            ctx, char_name, df, engine, guild
        )

    else:
        return False

    initiative_num = 0
    dex_mod = floor((character["dex"] - 10) / 2)
    init_string = f"1d20{ParseModifiers(f'{dex_mod}')}"
    if not overwrite:
        if guild.initiative is not None:
            # print("In initiative")
            try:
                roll = d20.roll(init_string)
                initiative_num = roll.total
            except Exception:
                initiative_num = 0

    if overwrite:
        async with async_session() as session:
            query = await session.execute(select(STF_tracker).where(func.lower(STF_tracker.name) == char_name.lower()))
            character_data = query.scalars().one()

            character_data.max_hp = character["hp"]
            character_data.max_stamina = character["stamina"]
            character_data.char_class = character["class"]
            character_data.base_eac = character["base_eac"]
            character_data.base_kac = character["base_kac"]
            character_data.level = character["level"]
            character_data.max_resolve = floor(character["level"] / 2) if character["level"] > 2 else 1
            character_data.key_ability = character["key_ability"]
            character_data.str = character["str"]
            character_data.dex = character["dex"]
            character_data.con = character["con"]
            character_data.itl = character["itl"]
            character_data.wis = character["wis"]
            character_data.cha = character["cha"]
            character_data.fort_pof = character["fort"]
            character_data.reflex_prof = character["reflex"]
            character_data.will_prof = character["will"]

            character_data.acrobatics = character["acrobatics"]
            character_data.athletics = character["athletics"]
            character_data.bluff = character["bluff"]
            character_data.computers = character["computers"]
            character_data.culture = character["culture"]
            character_data.diplomacy = character["diplomacy"]
            character_data.disguise = character["disguise"]
            character_data.engineering = character["engineering"]
            character_data.intimidate = character["intimidate"]
            character_data.life_science = character["life_science"]
            character_data.medicine = character["medicine"]
            character_data.mysticism = character["mysticism"]
            character_data.perception = character["perception"]
            character_data.physical_science = character["physical_science"]
            character_data.piloting = character["piloting"]
            character_data.sense_motive = character["sense_motive"]
            character_data.sleight_of_hand = character["sleight_of_hand"]
            character_data.stealth = character["stealth"]
            character_data.survival = character["survival"]

            character_data.spells = spells
            character_data.attacks = attacks

            await session.commit()

    else:
        async with async_session() as session:
            async with session.begin():
                new_char = STF_tracker(
                    name=char_name,
                    init=initiative_num,
                    player=True if "npc" not in character.keys() else False,
                    user=ctx.user.id,
                    current_hp=character["hp"],
                    current_stamina=character["stamina"],
                    max_stamina=character["stamina"],
                    max_hp=character["hp"],
                    temp_hp=0,
                    init_string=init_string,
                    active=True,
                    level=character["level"],
                    base_eac=character["base_eac"],
                    base_kac=character["base_kac"],
                    bab=character["bab"],
                    max_resolve=floor(character["level"] / 2) if character["level"] > 2 else 1,
                    resolve=floor(character["level"] / 2) if character["level"] > 2 else 1,
                    key_ability=character["key_ability"],
                    str=character["str"],
                    dex=character["dex"],
                    con=character["con"],
                    itl=character["itl"],
                    wis=character["wis"],
                    cha=character["cha"],
                    # Saves
                    fort=character["fort"],
                    will=character["will"],
                    reflex=character["reflex"],
                    acrobatics=character["acrobatics"],
                    athletics=character["athletics"],
                    bluff=character["bluff"],
                    computers=character["computers"],
                    culture=character["culture"],
                    diplomacy=character["diplomacy"],
                    disguise=character["disguise"],
                    engineering=character["engineering"],
                    intimidate=character["intimidate"],
                    life_science=character["life_science"],
                    medicine=character["medicine"],
                    mysticism=character["mysticism"],
                    perception=character["perception"],
                    physical_science=character["physical_science"],
                    piloting=character["piloting"],
                    sense_motive=character["sense_motive"],
                    sleight_of_hand=character["sleight_of_hand"],
                    stealth=character["stealth"],
                    survival=character["survival"],
                    attacks=attacks,
                )
                session.add(new_char)
                await session.commit()

        Character = await get_STF_Character(char_name, ctx, guild=guild, engine=engine)
        await Character.update()

    return True

    # except Exception:
    #     logging.warning("stf_g_sheet_import")
    #     return False


async def stf_g_sheet_character_import(ctx: discord.ApplicationContext, char_name: str, df, engine, guild):
    logging.info("g-sheet-char")
    try:
        df.rename(
            columns={
                "Starfinder Character Sheet:": "a",
                "Starfinder Character Sheet: ": "a",
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
        "class": f"{df.b[1]} {df.d[1]}",
        "hp": int(df.b[2]),
        "stamina": int(df.d[2]),
        "str": int(df.b[3]),
        "dex": int(df.b[4]),
        "con": int(df.b[5]),
        "itl": int(df.d[3]),
        "wis": int(df.d[4]),
        "cha": int(df.d[5]),
        "base_eac": int(df.b[6]),
        "base_kac": int(df.d[6]),
        "bab": int(df.e[7]),
        "key_ability": interpret(df.e[8]),
        "fort": await strip_mod(df.b[8]),
        "reflex": await strip_mod(df.b[9]),
        "will": await strip_mod(df.b[10]),
        "acrobatics": await strip_mod(df.b[12]),
        "athletics": await strip_mod(df.b[13]),
        "bluff": await strip_mod(df.b[14]),
        "computers": await strip_mod(df.b[15]),
        "culture": await strip_mod(df.b[16]),
        "diplomacy": await strip_mod(df.b[17]),
        "disguise": await strip_mod(df.b[18]),
        "engineering": await strip_mod(df.b[19]),
        "intimidate": await strip_mod(df.b[20]),
        "life_science": await strip_mod(df.b[21]),
        "medicine": await strip_mod(df.b[22]),
        "mysticism": await strip_mod(df.b[23]),
        "perception": await strip_mod(df.b[24]),
        "physical_science": await strip_mod(df.b[25]),
        "piloting": await strip_mod(df.b[26]),
        "sense_motive": await strip_mod(df.b[27]),
        "sleight_of_hand": await strip_mod(df.b[28]),
        "stealth": await strip_mod(df.b[29]),
        "survival": await strip_mod(df.b[30]),
    }

    spells = {}
    attacks = {}
    items = []
    resistances = {"resist": {}, "weak": {}, "immune": {}}

    # Attacks
    for i in range(11, (len(df.d) - 1)):
        if df.d[i] == "Name" and type(df.e[i]) == str:
            print(df.e[i])

            attack_data = {
                "type": df.f[i],
                "attk_bonus": df.e[i + 1],
                "dmg_type": df.g[i + 1],
                "dmg_die_num": df.e[i + 2],
                "dmg_die": df.f[i + 2],
                "dmg_bonus": df.g[i + 2],
            }
            traits = []
            try:
                traits.extend(df.e[i + 3]).split(",")
            except Exception:
                pass
            attack_data["traits"] = traits

            attacks[df.e[i]] = attack_data

    return character, spells, attacks, items, resistances


async def strip_mod(input: str):
    if type(input) == int:
        return input
    elif type(input) == str:
        try:
            return int(input)
        except Exception:
            if input[0] == "+":
                return input[1:]
    else:
        return 0
