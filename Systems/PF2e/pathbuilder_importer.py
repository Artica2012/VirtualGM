# Pathbuilder_importer.py

# Code to facilitate the importing of data directly from pathbuilder
import asyncio
import logging
import math
import os
from math import floor

import aiohttp
import discord
from dotenv import load_dotenv
from sqlalchemy import select, false, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import d20
from Backend.Database.database_models import get_macro, get_tracker, get_condition
from Backend.utils.error_handling_reporting import ErrorReport
from Backend.utils.Tracker_Getter import get_tracker_model
from Backend.utils.utils import get_guild

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")


# Import a PF2e character from pathbuilder
async def pathbuilder_import(
    ctx: discord.ApplicationContext, engine, bot, name: str, pb_char_code: str, image: str = None
):
    stats = {}
    macro = {}

    # import json
    paramaters = {"id": pb_char_code}

    async with aiohttp.ClientSession() as session:
        pb_url = "https://pathbuilder2e.com/json.php"
        async with session.get(pb_url, params=paramaters, verify_ssl=False) as resp:
            pb = await resp.json(content_type="text/html")
            # print(pb)

    if pb["success"] is False:
        await ctx.channel.send("Unsuccessful Pathbuilder Export. Please try to export again.", delete_after=90)
        return False
    try:
        # Interpeting the JSON
        stats["level"] = pb["build"]["level"]
        # print(stats["level"])
        # print(stats['level'])

        # Modifiers
        stats["str_mod"] = floor((pb["build"]["abilities"]["str"] - 10) / 2)
        # print(stats['str_mod'])
        stats["dex_mod"] = floor((pb["build"]["abilities"]["dex"] - 10) / 2)
        stats["con_mod"] = floor((pb["build"]["abilities"]["con"] - 10) / 2)
        stats["int_mod"] = floor((pb["build"]["abilities"]["int"] - 10) / 2)
        stats["wis_mod"] = floor((pb["build"]["abilities"]["wis"] - 10) / 2)
        stats["cha_mod"] = floor((pb["build"]["abilities"]["cha"] - 10) / 2)

        # AC
        stats["ac"] = pb["build"]["acTotal"]["acTotal"]
        stats["hp"] = (
            pb["build"]["attributes"]["ancestryhp"]
            + pb["build"]["attributes"]["classhp"]
            + pb["build"]["attributes"]["bonushp"]
            + pb["build"]["attributes"]["bonushpPerLevel"]
            + stats["con_mod"]
            + (
                (stats["level"] - 1)
                * (
                    pb["build"]["attributes"]["classhp"]
                    + pb["build"]["attributes"]["bonushpPerLevel"]
                    + stats["con_mod"]
                )
            )
        )

        # Initiative
        stats["initiative"] = stats["wis_mod"] + pb["build"]["proficiencies"]["perception"] + stats["level"]
        stats["init_string"] = f"1d20+{stats['initiative']}"

        # Saves
        stats["fort"] = stats["con_mod"] + pb["build"]["proficiencies"]["fortitude"] + stats["level"]
        stats["will"] = stats["wis_mod"] + pb["build"]["proficiencies"]["will"] + stats["level"]
        stats["reflex"] = stats["dex_mod"] + pb["build"]["proficiencies"]["reflex"] + stats["level"]

        # DC
        dc_list = []
        dc_list.append(
            stats[f"{pb['build']['keyability']}_mod"] + pb["build"]["proficiencies"]["classDC"] + stats["level"]
        )
        dc_list.append(pb["build"]["proficiencies"]["castingArcane"] + stats["int_mod"] + stats["level"])
        dc_list.append(pb["build"]["proficiencies"]["castingDivine"] + stats["wis_mod"] + stats["level"])
        dc_list.append(pb["build"]["proficiencies"]["castingPrimal"] + stats["wis_mod"] + stats["level"])
        dc_list.append(pb["build"]["proficiencies"]["castingOccult"] + stats["cha_mod"] + stats["level"])
        stats["dc"] = 10 + max(dc_list)

        # Stats

        macro["perception"] = stats["wis_mod"] + pb["build"]["proficiencies"]["perception"] + stats["level"]

        untrained_prof = 0
        for item in pb["build"]["feats"]:
            if "Untrained Improvisation" in item:
                if stats["level"] < 7:
                    untrained_prof = math.floor(stats["level"] / 2)
                else:
                    untrained_prof = stats["level"]
        # print(untrained_prof)

        if pb["build"]["proficiencies"]["athletics"] == 0:
            macro["athletics"] = stats["str_mod"] + untrained_prof
        else:
            macro["athletics"] = stats["str_mod"] + pb["build"]["proficiencies"]["athletics"] + stats["level"]

        if pb["build"]["proficiencies"]["acrobatics"] == 0:
            macro["acrobatics"] = stats["dex_mod"] + untrained_prof
        else:
            macro["acrobatics"] = stats["dex_mod"] + pb["build"]["proficiencies"]["acrobatics"] + stats["level"]

        if pb["build"]["proficiencies"]["arcana"] == 0:
            macro["arcana"] = stats["int_mod"] + untrained_prof
        else:
            macro["arcana"] = stats["int_mod"] + pb["build"]["proficiencies"]["arcana"] + stats["level"]

        if pb["build"]["proficiencies"]["crafting"] == 0:
            macro["crafting"] = stats["int_mod"] + untrained_prof
        else:
            macro["crafting"] = stats["int_mod"] + pb["build"]["proficiencies"]["crafting"] + stats["level"]

        if pb["build"]["proficiencies"]["deception"] == 0:
            macro["deception"] = stats["cha_mod"] + untrained_prof
        else:
            macro["deception"] = stats["cha_mod"] + pb["build"]["proficiencies"]["deception"] + stats["level"]

        if pb["build"]["proficiencies"]["diplomacy"] == 0:
            macro["diplomacy"] = stats["cha_mod"] + untrained_prof
        else:
            macro["diplomacy"] = stats["cha_mod"] + pb["build"]["proficiencies"]["diplomacy"] + stats["level"]

        if pb["build"]["proficiencies"]["intimidation"] == 0:
            macro["intimidation"] = stats["cha_mod"] + untrained_prof
        else:
            macro["intimidation"] = stats["cha_mod"] + pb["build"]["proficiencies"]["intimidation"] + stats["level"]

        if pb["build"]["proficiencies"]["medicine"] == 0:
            macro["medicine"] = stats["wis_mod"] + untrained_prof
        else:
            macro["medicine"] = stats["wis_mod"] + pb["build"]["proficiencies"]["medicine"] + stats["level"]

        if pb["build"]["proficiencies"]["nature"] == 0:
            macro["nature"] = stats["wis_mod"] + untrained_prof
        else:
            macro["nature"] = stats["wis_mod"] + pb["build"]["proficiencies"]["nature"] + stats["level"]

        if pb["build"]["proficiencies"]["occultism"] == 0:
            macro["occultism"] = stats["int_mod"] + untrained_prof
        else:
            macro["occultism"] = stats["int_mod"] + pb["build"]["proficiencies"]["occultism"] + stats["level"]

        if pb["build"]["proficiencies"]["performance"] == 0:
            macro["performance"] = stats["cha_mod"] + untrained_prof
        else:
            macro["performance"] = stats["cha_mod"] + pb["build"]["proficiencies"]["performance"] + stats["level"]

        if pb["build"]["proficiencies"]["religion"] == 0:
            macro["religion"] = stats["wis_mod"] + untrained_prof
        else:
            macro["religion"] = stats["wis_mod"] + pb["build"]["proficiencies"]["religion"] + stats["level"]

        if pb["build"]["proficiencies"]["society"] == 0:
            macro["society"] = stats["int_mod"] + untrained_prof
        else:
            macro["society"] = stats["int_mod"] + pb["build"]["proficiencies"]["society"] + stats["level"]

        if pb["build"]["proficiencies"]["stealth"] == 0:
            macro["stealth"] = stats["dex_mod"] + untrained_prof
        else:
            macro["stealth"] = stats["dex_mod"] + pb["build"]["proficiencies"]["stealth"] + stats["level"]

        if pb["build"]["proficiencies"]["survival"] == 0:
            macro["survival"] = stats["wis_mod"] + untrained_prof
        else:
            macro["survival"] = stats["wis_mod"] + pb["build"]["proficiencies"]["survival"] + stats["level"]

        if pb["build"]["proficiencies"]["thievery"] == 0:
            macro["thievery"] = stats["dex_mod"] + untrained_prof
        else:
            macro["thievery"] = stats["dex_mod"] + pb["build"]["proficiencies"]["thievery"] + stats["level"]
    except Exception:
        return False

    # Write the data

    try:
        # Start off by checking to see if the character already exists, and if so, delete it before importing
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)
        Tracker = await get_tracker(ctx, id=guild.id)
        Condition = await get_condition(ctx, id=guild.id)
        Macro = await get_macro(ctx, id=guild.id)

        initiative = 0
        if guild.initiative is not None:
            roll = d20.roll(stats["init_string"])
            initiative = roll.total
            # print(f"initiative {initiative}")
        if guild.system != "PF2":
            return False
        else:
            # Check to see if the character already exists
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(func.lower(Tracker.name) == name.lower()))
                character = char_result.scalars().all()
            if len(character) > 0:  # If character already exists, update the relevant parts and make overwrite = True
                overwrite = True
                async with async_session() as session:
                    char_result = await session.execute(select(Tracker).where(Tracker.name == name))
                    char = char_result.scalars().one()

                    char.init = initiative
                    char.init_string = stats["init_string"]
                    char.current_hp = stats["hp"]
                    char.max_hp = stats["hp"]

                    if image is not None:
                        char.pic = image

                    await session.commit()
            else:
                overwrite = False  # If not overwriting, just write the character
                async with async_session() as session:
                    async with session.begin():
                        new_char = Tracker(
                            name=name,
                            init_string=stats["init_string"],
                            init=initiative,
                            player=True,
                            user=ctx.user.id,
                            current_hp=stats["hp"],
                            max_hp=stats["hp"],
                            temp_hp=0,
                            pic=image,
                        )
                        session.add(new_char)
                    await session.commit()

            Tracker_Model = await get_tracker_model(ctx, bot, guild=guild, engine=engine)
            await Tracker_Model.init_integrity()
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == name))
                character = result.scalars().one()
            if overwrite:  # If we are overwriting, just delete the stat conditions
                async with async_session() as session:
                    result = await session.execute(
                        select(Condition)
                        .where(Condition.character_id == character.id)
                        .where(Condition.visible == false())
                    )
                    invisible_conditions = result.scalars().all()
                for con in invisible_conditions:
                    await asyncio.sleep(0)
                    async with async_session() as session:
                        await session.delete(con)
                        await session.commit()

            async with session.begin():
                new_con = Condition(
                    character_id=character.id, title="AC", number=int(stats["ac"]), counter=True, visible=False
                )
                session.add(new_con)

                new_con = Condition(
                    character_id=character.id, title="Fort", number=int(stats["fort"]), counter=True, visible=False
                )
                session.add(new_con)

                new_con = Condition(
                    character_id=character.id, title="Reflex", number=int(stats["reflex"]), counter=True, visible=False
                )
                session.add(new_con)

                new_con = Condition(
                    character_id=character.id, title="Will", number=int(stats["will"]), counter=True, visible=False
                )
                session.add(new_con)

                new_con = Condition(
                    character_id=character.id, title="DC", number=int(stats["dc"]), counter=True, visible=False
                )
                session.add(new_con)
            await session.commit()

            # If overwriting, delete all macros
            if overwrite:  # If we are overwriting, just delete the stat conditions
                async with async_session() as session:
                    result = await session.execute(select(Macro).where(Macro.character_id == character.id))
                    macros_to_delete = result.scalars().all()
                for del_macro in macros_to_delete:
                    await asyncio.sleep(0)
                    async with async_session() as session:
                        await session.delete(del_macro)
                        await session.commit()

            macro_keys = macro.keys()
            async with session.begin():
                for key in macro_keys:
                    await asyncio.sleep(0)
                    if macro[key] >= 0:
                        new_macro = Macro(character_id=character.id, name=key.title(), macro=f"1d20+{macro[key]}")
                    else:
                        new_macro = Macro(character_id=character.id, name=key.title(), macro=f"1d20{macro[key]}")
                    session.add(new_macro)
            await session.commit()
        # await engine.dispose()
        if overwrite:
            return f"Successfully updated {name}."
        else:
            return f"Successfully imported {name}."

    except Exception as e:
        logging.warning(f"create_macro: {e}")
        report = ErrorReport(ctx, "pathbuilder importer", e, bot)
        await report.report()
        return False
