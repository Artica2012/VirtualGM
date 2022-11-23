# Pathbuilder_importer.py

# Code to facilitate the importing of data directly from pathbuilder
import asyncio
import os
from math import floor

import aiohttp
import discord
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from database_models import Global
from database_models import get_macro, get_tracker, get_condition
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport
from initiative import init_integrity_check, get_init_list

load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
    USERNAME = os.getenv('Username')
    PASSWORD = os.getenv('Password')
    HOSTNAME = os.getenv('Hostname')
    PORT = os.getenv('PGPort')
else:
    TOKEN = os.getenv('BETA_TOKEN')
    USERNAME = os.getenv('BETA_Username')
    PASSWORD = os.getenv('BETA_Password')
    HOSTNAME = os.getenv('BETA_Hostname')
    PORT = os.getenv('BETA_PGPort')

GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
DATABASE = os.getenv('DATABASE')

# Import a PF2e character from pathbuilder
async def pathbuilder_import(ctx: discord.ApplicationContext, engine, bot,
                             name: str, pb_char_code: str):
    stats = {}
    macro = {}

    # import json
    paramaters = {
        'id': pb_char_code
    }

    async with aiohttp.ClientSession() as session:
        pb_url = 'https://pathbuilder2e.com/json.php'
        async with session.get(pb_url, params=paramaters, verify_ssl=False) as resp:
            pb = await resp.json(content_type='text/html')
            # print(pb)

    if pb['success'] == False:
        await ctx.channel.send("Unsuccessful Pathbuilder Export. Please try to export again.", delete_after=90)
        return False
    try:

        # Interpeting the JSON
        stats['level'] = pb['build']['level']
        print(stats['level'])
        # print(stats['level'])

        # Modifiers
        stats['str_mod'] = floor((pb['build']['abilities']['str'] - 10) / 2)
        # print(stats['str_mod'])
        stats['dex_mod'] = floor((pb['build']['abilities']['dex'] - 10) / 2)
        stats['con_mod'] = floor((pb['build']['abilities']['con'] - 10) / 2)
        stats['int_mod'] = floor((pb['build']['abilities']['int'] - 10) / 2)
        stats['wis_mod'] = floor((pb['build']['abilities']['wis'] - 10) / 2)
        stats['cha_mod'] = floor((pb['build']['abilities']['cha'] - 10) / 2)

        # AC
        stats['ac'] = pb['build']['acTotal']['acTotal']
        stats['hp'] = pb['build']['attributes']['ancestryhp'] + pb['build']['attributes']['classhp'] + \
                      pb['build']['attributes']['bonushp'] + (stats['level'] * (
                    pb['build']['attributes']['classhp'] + pb['build']['attributes']['bonushpPerLevel']))

        # Initiative
        stats['initiative'] = stats['wis_mod'] + pb['build']['proficiencies']['perception'] + stats['level']
        stats['init_string'] = f"1d20+{stats['initiative']}"

        # Saves
        stats['fort'] = stats['con_mod'] + pb['build']['proficiencies']['fortitude'] + stats['level']
        stats['will'] = stats['wis_mod'] + pb['build']['proficiencies']['will'] + stats['level']
        stats['reflex'] = stats['dex_mod'] + pb['build']['proficiencies']['reflex'] + stats['level']

        # DC
        dc_list = []
        dc_list.append(stats[f"{pb['build']['keyability']}_mod"] + pb['build']['proficiencies']['classDC'] + stats['level'])
        dc_list.append(pb['build']['proficiencies']['castingArcane'] + stats['int_mod'] + stats['level'])
        dc_list.append(pb['build']['proficiencies']['castingDivine'] + stats['wis_mod'] + stats['level'])
        dc_list.append(pb['build']['proficiencies']['castingPrimal'] + stats['wis_mod'] + stats['level'])
        dc_list.append(pb['build']['proficiencies']['castingOccult'] + stats['cha_mod'] + stats['level'])
        stats['dc'] = 10 + max(dc_list)

        # Stats

        macro['perception'] = stats['wis_mod'] + pb['build']['proficiencies']['perception'] + stats['level']

        if pb['build']['proficiencies']['athletics'] == 0:
            macro['athletics'] = stats['str_mod']
        else:
            macro['athletics'] = stats['str_mod'] + pb['build']['proficiencies']['athletics'] + stats['level']

        if pb['build']['proficiencies']['acrobatics'] == 0:
            macro['acrobatics'] = stats['dex_mod']
        else:
            macro['acrobatics'] = stats['dex_mod'] + pb['build']['proficiencies']['acrobatics'] + stats['level']

        if pb['build']['proficiencies']['arcana'] == 0:
            macro['arcana'] = stats['int_mod']
        else:
            macro['arcana'] = stats['int_mod'] + pb['build']['proficiencies']['arcana'] + stats['level']

        if pb['build']['proficiencies']['crafting'] == 0:
            macro['crafting'] = stats['int_mod']
        else:
            macro['crafting'] = stats['int_mod'] + pb['build']['proficiencies']['crafting'] + stats['level']

        if pb['build']['proficiencies']['deception'] == 0:
            macro['deception'] = stats['cha_mod']
        else:
            macro['deception'] = stats['cha_mod'] + pb['build']['proficiencies']['deception'] + stats['level']

        if pb['build']['proficiencies']['diplomacy'] == 0:
            macro['diplomacy'] = stats['cha_mod']
        else:
            macro['diplomacy'] = stats['cha_mod'] + pb['build']['proficiencies']['diplomacy'] + stats['level']

        if pb['build']['proficiencies']['intimidation'] == 0:
            macro['intimidation'] = stats['cha_mod']
        else:
            macro['intimidation'] = stats['cha_mod'] + pb['build']['proficiencies']['intimidation'] + stats['level']

        if pb['build']['proficiencies']['medicine'] == 0:
            macro['medicine'] = stats['wis_mod']
        else:
            macro['medicine'] = stats['wis_mod'] + pb['build']['proficiencies']['medicine'] + stats['level']

        if pb['build']['proficiencies']['nature'] == 0:
            macro['nature'] = stats['wis_mod']
        else:
            macro['nature'] = stats['wis_mod'] + pb['build']['proficiencies']['nature'] + stats['level']

        if pb['build']['proficiencies']['occultism'] == 0:
            macro['occultism'] = stats['int_mod']
        else:
            macro['occultism'] = stats['int_mod'] + pb['build']['proficiencies']['occultism'] + stats['level']

        if pb['build']['proficiencies']['performance'] == 0:
            macro['performance'] = stats['cha_mod']
        else:
            macro['performance'] = stats['cha_mod'] + pb['build']['proficiencies']['performance'] + stats['level']

        if pb['build']['proficiencies']['religion'] == 0:
            macro['religion'] = stats['wis_mod']
        else:
            macro['religion'] = stats['wis_mod'] + pb['build']['proficiencies']['religion'] + stats['level']

        if pb['build']['proficiencies']['society'] == 0:
            macro['society'] = stats['int_mod']
        else:
            macro['society'] = stats['int_mod'] + pb['build']['proficiencies']['society'] + stats['level']

        if pb['build']['proficiencies']['stealth'] == 0:
            macro['stealth'] = stats['dex_mod']
        else:
            macro['stealth'] = stats['dex_mod'] + pb['build']['proficiencies']['stealth'] + stats['level']

        if pb['build']['proficiencies']['survival'] == 0:
            macro['survival'] = stats['wis_mod']
        else:
            macro['survival'] = stats['wis_mod'] + pb['build']['proficiencies']['survival'] + stats['level']

        if pb['build']['proficiencies']['thievery'] == 0:
            macro['thievery'] = stats['dex_mod']
        else:
            macro['thievery'] = stats['dex_mod'] + pb['build']['proficiencies']['thievery'] + stats['level']
    except Exception as e:
        return False
    # Write the data

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        Macro = await get_macro(ctx, engine, id=guild.id)

        initiative = 0
        if guild.initiative != None:
            dice = DiceRoller('')
            try:
                # print(f"Init: {init}")
                initiative = int(stats['init_string'])
            except:
                try:
                    roll = await dice.plain_roll(stats['init_string'])
                    initiative = roll[1]
                    if type(initiative) != int:
                        initiative = 0
                except:
                    initiative = 0
        if guild.system != 'PF2':
            return False
        else:
            async with session.begin():
                new_char = Tracker(
                    name=name,
                    init_string=stats['init_string'],
                    init=initiative,
                    player=True,
                    user=ctx.user.id,
                    current_hp=stats['hp'],
                    max_hp=stats['hp'],
                    temp_hp=0
                )
                session.add(new_char)
            await session.commit()

            if guild.initiative != None:
                if not await init_integrity_check(ctx, guild.initiative, guild.saved_order, engine):
                    # print(f"integrity check was false: init_pos: {guild.initiative}")
                    for pos, row in enumerate(await get_init_list(ctx, engine)):
                        await asyncio.sleep(0)
                        if row.name == guild.saved_order:
                            guild.initiative = pos
                            # print(f"integrity checked init_pos: {guild.initiative}")
                            await session.commit()
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == name))
                character = result.scalars().one()

            async with session.begin():
                new_con = Condition(
                    character_id=character.id,
                    title='AC',
                    number=int(stats['ac']),
                    counter=True,
                    visible=False
                )
                session.add(new_con)

                new_con = Condition(
                    character_id=character.id,
                    title='Fort',
                    number=int(stats['fort']),
                    counter=True,
                    visible=False
                )
                session.add(new_con)

                new_con = Condition(
                    character_id=character.id,
                    title='Reflex',
                    number=int(stats['reflex']),
                    counter=True,
                    visible=False
                )
                session.add(new_con)

                new_con = Condition(
                    character_id=character.id,
                    title='Will',
                    number=int(stats['will']),
                    counter=True,
                    visible=False
                )
                session.add(new_con)

                new_con = Condition(
                    character_id=character.id,
                    title='DC',
                    number=int(stats['dc']),
                    counter=True,
                    visible=False
                )
                session.add(new_con)
            await session.commit()

            macro_keys = macro.keys()
            async with session.begin():
                for key in macro_keys:
                    await asyncio.sleep(0)
                    if macro[key] >= 0:
                        new_macro = Macro(
                            character_id=character.id,
                            name=key.title(),
                            macro=f"1d20+{macro[key]}"
                        )
                    else:
                        new_macro = Macro(
                            character_id=character.id,
                            name=key.title(),
                            macro=f"1d20{macro[key]}"
                        )
                    session.add(new_macro)
            await session.commit()
        await engine.dispose()
        return True
    except Exception as e:
        print(f'create_macro: {e}')
        report = ErrorReport(ctx, "pathbuilder importer", e, bot)
        await report.report()
        return False
