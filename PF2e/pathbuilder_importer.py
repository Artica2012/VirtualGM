# Pathbuilder_importer.py

# Code to facilitate the importing of data directly from pathbuilder
import asyncio
from math import floor
import os
import aiohttp
import discord
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import sqlalchemy as db
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_, func
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.sql.ddl import DropTable
import PF2e.pf2_functions

from database_models import Global, Base, TrackerTable, ConditionTable, MacroTable
from database_models import get_tracker_table, get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport, error_not_initialized
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

async def pathbuilder_import(ctx: discord.ApplicationContext, engine, bot,
                              name:str, pb_char_code:str):
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
            print(pb)

    # Interpeting the JSON
    stats['level'] = pb['build']['level']
    print(stats['level'])

    # Modifiers
    stats['str_mod'] = floor(pb['abilities']['str'] - 10 / 2)
    stats['dex_mod'] = floor(pb['abilities']['dex'] - 10 / 2)
    stats['con_mod'] = floor(pb['abilities']['con'] - 10 / 2)
    stats['int_mod'] = floor(pb['abilities']['int'] - 10 / 2)
    stats['wis_mod'] = floor(pb['abilities']['wis'] - 10 / 2)
    stats['cha_mod'] = floor(pb['abilities']['cha'] - 10 / 2)

    # AC
    stats['ac'] = pb['acTotal']['acTotal']
    stats['hp'] = pb['attributes']['anscestryhp'] + pb['attributes']['classhp'] + pb['attributes']['bonushp'] + (stats['level'] * (pb['attributes']['classhp']+pb['attributes']['bonushpPerLevel']))

    # Initiative
    stats['initiative'] = stats['wis_mod'] + pb['proficiencies']['perception'] + stats['level']
    stats['init_string'] = f"1d20+{stats['initiative']}"

    # Saves
    stats['fort'] = stats['con_mod'] + pb['proficiencies']['fortitude'] + stats['level']
    stats['will'] = stats['wis_mod'] + pb['proficiencies']['will'] + stats['level']
    stats['reflex'] = stats['dex_mod'] + pb['proficiencies']['reflex'] + stats['level']

    # DC
    dc_list = []
    dc_list.append(stats[f"{pb['build']['keyability']}_mod"]+pb['proficiencies']['classDC']+stats['level'])
    dc_list.append(pb['proficiencies']['castingArcane']+stats['int_mod']+stats['level'])
    dc_list.append(pb['proficiencies']['castingDivine'] + stats['wis_mod'] + stats['level'])
    dc_list.append(pb['proficiencies']['castingPrimal'] + stats['wis_mod'] + stats['level'])
    dc_list.append(pb['proficiencies']['castingOccult'] + stats['cha_mod'] + stats['level'])
    stats['dc'] = max(dc_list)


    # Stats
    if pb['proficiencies']['acrobatics'] == 0:
        macro['acrobatics'] = stats['dex_mod']
    else:
        macro['acrobatics'] = stats['dex_mod'] + pb['proficiencies']['acrobatics'] + stats['level']

    if pb['proficiencies']['arcana'] == 0:
        macro['arcana'] = stats['int_mod']
    else:
        macro['arcana'] = stats['int_mod'] + pb['proficiencies']['arcana'] + stats['level']

    if pb['proficiencies']['crafting'] == 0:
        macro['crafting'] = stats['int_mod']
    else:
        macro['crafting'] = stats['int_mod'] + pb['proficiencies']['crafting'] + stats['level']

    if pb['proficiencies']['deception'] == 0:
        macro['deception'] = stats['cha_mod']
    else:
        macro['deception'] = stats['cha_mod'] + pb['proficiencies']['deception'] + stats['level']

    if pb['proficiencies']['diplomacy'] == 0:
        macro['diplomacy'] = stats['cha_mod']
    else:
        macro['diplomacy'] = stats['cha_mod'] + pb['proficiencies']['diplomacy'] + stats['level']

    if pb['proficiencies']['intimidation'] == 0:
        macro['intimidation'] = stats['cha_mod']
    else:
        macro['intimidation'] = stats['cha_mod'] + pb['proficiencies']['intimidation'] + stats['level']

    if pb['proficiencies']['medicine'] == 0:
        macro['medicine'] = stats['wis_mod']
    else:
        macro['medicine'] = stats['wis_mod'] + pb['proficiencies']['medicine'] + stats['level']

    if pb['proficiencies']['nature'] == 0:
        macro['nature'] = stats['wis_mod']
    else:
        macro['nature'] = stats['wis_mod'] + pb['proficiencies']['nature'] + stats['level']

    if pb['proficiencies']['occultism'] == 0:
        macro['occultism'] = stats['int_mod']
    else:
        macro['occultism'] = stats['int_mod'] + pb['proficiencies']['occultism'] + stats['level']

    if pb['proficiencies']['performance'] == 0:
        macro['performance'] = stats['cha_mod']
    else:
        macro['performance'] = stats['cha_mod'] + pb['proficiencies']['performance'] + stats['level']

    if pb['proficiencies']['religion'] == 0:
        macro['religion'] = stats['wis_mod']
    else:
        macro['religion'] = stats['wis_mod'] + pb['proficiencies']['religion'] + stats['level']

    if pb['proficiencies']['society'] == 0:
        macro['society'] = stats['int_mod']
    else:
        macro['society'] = stats['int_mod'] + pb['proficiencies']['society'] + stats['level']

    if pb['proficiencies']['stealth'] == 0:
        macro['stealth'] = stats['dex_mod']
    else:
        macro['stealth'] = stats['dex_mod'] + pb['proficiencies']['stealth'] + stats['level']

    if pb['proficiencies']['survival'] == 0:
        macro['survival'] = stats['wis_mod']
    else:
        macro['survival'] = stats['wis_mod'] + pb['proficiencies']['survival'] + stats['level']

    if pb['proficiencies']['thievery'] == 0:
        macro['thievery'] = stats['dex_mod']
    else:
        macro['thievery'] = stats['dex_mod'] + pb['proficiencies']['thievery'] + stats['level']

    # Write the data
    metadata = db.Metadata()

    try:
        emp = await get_tracker_table(ctx, metadata, engine)
        con = await get_condition_table(ctx, metadata, engine)
        macro_table = await get_macro_table(ctx, metadata, engine)
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
                stmt = emp.insert().values(
                    name=name,
                    init_string=stats['init_string'],
                    init=initiative,
                    player=True,
                    user=ctx.user.id,
                    current_hp=stats['hp'],
                    max_hp=stats['hp'],
                    temp_hp=0
                )
                async with engine.begin() as conn:
                    result = await conn.execute(stmt)

                    if guild.initiative != None:
                        if not await init_integrity_check(ctx, guild.initiative, guild.saved_order, engine):
                            # print(f"integrity check was false: init_pos: {guild.initiative}")
                            for pos, row in enumerate(await get_init_list(ctx, engine)):
                                await asyncio.sleep(0)
                                if row[1] == guild.saved_order:
                                    guild.initiative = pos
                                    # print(f"integrity checked init_pos: {guild.initiative}")
                                    await session.commit()
                    id_stmt = emp.select().where(emp.c.name == name)
                    id_data = []
                    for row in await conn.execute(id_stmt):
                        await asyncio.sleep(0)
                        id_data.append(row)

                    char_dicts = [{
                        'character_id': id_data[0][0],
                        'title': 'AC',
                        'number': int(stats['ac']),
                        'counter': True,
                        'visible': False
                    },
                        {
                            'character_id': id_data[0][0],
                            'title': 'Fort',
                            'number': int(stats['fort']),
                            'counter': True,
                            'visible': False
                        },
                        {
                            'character_id': id_data[0][0],
                            'title': 'Reflex',
                            'number': int(stats['reflex']),
                            'counter': True,
                            'visible': False
                        },
                        {
                            'character_id': id_data[0][0],
                            'title': 'Will',
                            'number': int(stats['will']),
                            'counter': True,
                            'visible': False
                        },
                        {
                            'character_id': id_data[0][0],
                            'title': 'DC',
                            'number': int(stats['dc']),
                            'counter': True,
                            'visible': False
                        },
                    ]

                    con_stmt = con.insert().values(
                        char_dicts
                    )
                    await conn.execute(con_stmt)

                    macro_keys = macro.keys()
                    for key in macro_keys:
                        await asyncio.sleep(0)
                        macro_stmt = macro_table.insert().values(
                            character_id=id_data[0][0],
                            name=key,
                            macro=f"1d20+{macro[key]}"
                        )
                        await conn.execute(macro_stmt)
                await engine.dispose()
    except Exception as e:
        print(f'create_macro: {e}')
        report = ErrorReport(ctx, "pathbuilder importer", e, bot)
        await report.report()
        return False






