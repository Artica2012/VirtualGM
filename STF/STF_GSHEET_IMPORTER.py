import logging

import discord
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_STF_tracker
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA


async def stf_g_sheet_import(ctx: discord.ApplicationContext, char_name: str, base_url: str, engine=None, guild=None):
    # try:
    parsed_url = base_url.split("/")
    sheet_id = parsed_url[5]
    logging.warning(f"G-sheet import: ID - {sheet_id}")
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    df = pd.read_csv(url, header=[0])

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

    return True

    # except Exception:
    #     logging.warning("stf_g_sheet_import")
    #     return False
