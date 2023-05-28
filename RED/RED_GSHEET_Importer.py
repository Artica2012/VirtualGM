import logging

import d20
import discord
import numpy
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from RED.RED_Character import get_RED_Character
from database_models import get_RED_tracker
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild

Interpreter = {
    "Yes": True,
    "No": False,
    numpy.nan: "",
}


async def red_g_sheet_import(
    ctx: discord.ApplicationContext, char_name: str, base_url: str, engine=None, guild=None, image=None
):
    # try:
    parsed_url = base_url.split("/")
    # print(parsed_url)
    sheet_id = parsed_url[5]
    logging.warning(f"G-sheet import: ID - {sheet_id}")
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    df = pd.read_csv(url, header=[0])

    guild = await get_guild(ctx, guild)
    if engine is None:
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
    print(df)

    decision_header = headers[0].strip()

    if decision_header == "CyberpunkRED:":
        character = await red_g_sheet_character_import(ctx, char_name, df, engine, guild)
    else:
        return False

    init_string = f"1d10+{character['stats']['ref']['value']}"

    initiative_num = 0
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
            query = await session.execute(select(red_tracker).where(func.lower(red_tracker.name) == char_name.lower()))
            character_data = query.scalars().one()

            character_data.max_hp = character["hp"]
            character_data.char_class = character["role"]
            character_data.init_string = init_string
            character_data.level = character["level"]
            character_data.humanity = character["humanity"]
            character_data.stats = character["stats"]
            character_data.skills = character["skills"]
            character_data.attacks = character["attacks"]
            character_data.armor = character["armor"]
            character_data.cyber = character["cyber"]
            character_data.net = character["net"]

            if image is not None:
                character.pic = image

            await session.commit()

    else:
        async with async_session() as session:
            async with session.begin():
                new_char = red_tracker(
                    name=char_name,
                    init=initiative_num,
                    player=True if "npc" not in character.keys() else False,
                    user=ctx.user.id,
                    current_hp=character["hp"],
                    max_hp=character["hp"],
                    temp_hp=0,
                    init_string=init_string,
                    active=character["active"],
                    char_class=character["role"],
                    level=character["level"],
                    humanity=character["humanity"],
                    current_luck=character["stats"]["luck"]["value"],
                    stats=character["stats"],
                    skills=character["skills"],
                    attacks=character["attacks"],
                    armor=character["armor"],
                    cyber=character["cyber"],
                    net=character["net"],
                    # Functional Stuff
                    macros={},
                    bonuses={},
                    pic=image,
                )
                session.add(new_char)
            await session.commit()

    Character = await get_RED_Character(char_name, ctx, guild, engine)
    # Write the conditions
    # await write_resitances(resistance, Character, ctx, guild, engine)
    await Character.update()
    return True

    # except Exception:
    #     logging.warning("epf_g_sheet_import")
    #     return False


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
                "Unnamed: 8": "i",
                "Unnamed: 9": "j",
                "Unnamed: 10": "k",
            },
            inplace=True,
        )

    except Exception:
        return False

    character = {
        "name": df.a[1],
        "level": int(df.d[0]),
        "active": True,
        "role": df.a[3],
        "hp": df.d[2],
        "humanity": df.d[11],
        "cyber": {},
        "net": {},
    }
    stats = {}

    for i in range(4, 10):
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
    for i in range(11, len(df.a)):
        print(df.a[i])
        if type(df.a[i]) == str:
            try:
                skill_name = str(df.a[i]).lower()
                skill_name = skill_name.strip()
                level = int(df.b[i])
                stat = str(df.c[i]).lower()
                value = stats[stat]["value"] + level

                item = {"value": value, "stat": stat, "base": level}
                skills[skill_name] = item
                print(item)
            except Exception as e:
                logging.error(f"red-g-sheet-import: {e}, {i}")
    character["skills"] = skills
    print(skills)

    attacks = {}
    for i in range(11, len(df.e)):
        print(df.e[i], df.f[i], df.g[i], df.h[i])
        if type(df.e[i]) == str:
            if df.e[i] == "Name:":
                print(df.e[i], str(df.f[i]))
                try:
                    dmg_string = f"{df.f[i + 2]}{df.g[i + 2]}"
                    name = str(df.f[i])
                    attack_data = {
                        "skill": str(df.f[i + 1]).lower(),
                        "type": str(df.h[i + 1]).lower(),
                        "dmg": dmg_string,
                        "hands": int(df.f[i + 3]),
                        "rof": int(df.f[i + 4]),
                        "attk_bonus": int(df.f[i + 5]),
                        "autofire": Interpreter[df.f[i + 6]],
                        "autofire_ammt": int(df.h[i + 6]),
                        "attach": str(df.f[i + 7]),
                    }
                    attacks[name] = attack_data
                    print(attack_data)
                except Exception as e:
                    logging.error(f"red-g-sheet-import: {e}, {i}")
    print(attacks)
    character["attacks"] = attacks

    armor = {}
    for i in range(14, 17):
        if type(df.i[i]) == str:
            location = str(df.i[i])
            sp = df.j[i]
            penalty = df.k[i]
        armor[location] = {"sp": sp, "penalty": penalty}
    print(armor)
    character["armor"] = armor
    return character


async def gs_npc_skill_calc(skill_mod, level, stat_mod):
    if skill_mod is numpy.nan:
        return 0
    else:
        return int(skill_mod) - level - stat_mod
