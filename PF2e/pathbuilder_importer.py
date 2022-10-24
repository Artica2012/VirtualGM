# Pathbuilder_importer.py

# Code to facilitate the importing of data directly from pathbuilder

import aiohttp

async def pathbuilder_import(pb_char_code:str):

    # import json
    paramaters = {
        'id': pb_char_code
    }

    async with aiohttp.ClientSession() as session:
        pb_url = 'https://pathbuilder2e.com/json.php'
        async with session.get(pb_url, params=paramaters, verify_ssl=False) as resp:
            import_file = await resp.json(content_type='text/html')
            print(import_file)

    # Interpeting the JSON
