# Pathbuilder_importer.py

# Code to facilitate the importing of data directly from pathbuilder
from math import floor

import aiohttp

async def pathbuilder_import(pb_char_code:str):
    stats = {}
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

    #AC
    stats['ac'] = pb['acTotal']['acTotal']
    stats['hp'] = pb['attributes']['anscestryhp'] + pb['attributes']['classhp'] + pb['attributes']['bonushp'] + (stats['level'] * (pb['attributes']['classhp']+pb['attributes']['bonushpPerLevel']))
    # This is wrong VVVVVVVV Level should only be considered if proficieny is not untrained.
    stats['initiative'] = stats['wis_mod'] + pb['proficiencies']['perception'] + stats['level']
    stats['acrobatics'] = stats['dex_mod'] + pb['proficiencies']['acrobatics'] + stats['level']




