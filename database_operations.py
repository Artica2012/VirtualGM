# database_operations.py
import logging
import os

import sqlalchemy as db
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy import select

# imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import Global, Base, get_condition

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

url = f"postgresql+asyncpg://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{SERVER_DATA}"
# print(f"Engine URL: {url}")
engine = create_async_engine(url, echo=False, pool_size=20, max_overflow=-1)
lookup_url = f"postgresql+asyncpg://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}"
# print(f"Lookup URL: {lookup_url}")
look_up_engine = create_async_engine(lookup_url, echo=False, pool_size=10, max_overflow=-1, query_cache_size=150)


# Get the engine
def get_asyncio_db_engine(user, password, host, port, db):
    # url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    # # print(url)
    # # if not database_exists(url):
    # #     create_database(url)
    # engine = create_async_engine(url, echo=False, pool_size=5, max_overflow=-1, query_cache_size=80)
    # return engine
    if db == SERVER_DATA:
        # print("engine")
        return engine
    elif db == DATABASE:
        # print("lookup")
        return look_up_engine
    else:
        return None


def get_db_engine(user, password, host, port, db):
    url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    # print(url)
    # if not database_exists(url):
    #     create_database(url)
    engine = create_engine(url, pool_size=10, echo=False)
    return engine


async def update_tracker_table():
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(Global))
        guild = result.scalars().all()

    for row in guild:
        try:
            print(f"Updating {row.id}")
            alter_string = text(f'ALTER TABLE "Tracker_{row.id}" ADD pic varchar')
            async with async_session() as session:
                await session.execute(alter_string)
                await session.commit()
        except Exception as e:
            print(f"{row.id}, {e}")


async def update_con_table():
    total = 0
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(Global))
        guild = result.scalars().all()

    for row in guild:
        try:
            print(f"Updating {row.id}")
            alter_string = text(f'ALTER TABLE "Condition_{row.id}" ADD target INTEGER')
            async with async_session() as session:
                await session.execute(alter_string)
                await session.commit()
        except Exception as e:
            print(f"{row.id}, {e}")

    for row in guild:
        Condition = await get_condition(None, engine, id=row.id)
        async with async_session() as session:
            result = await session.execute(select(Condition))
            con_list = result.scalars().all()
        for condition_row in con_list:
            async with async_session() as session:
                result = await session.execute(select(Condition).where(Condition.id == condition_row.id))
                working_con = result.scalars().one()
                if working_con.target is None:
                    working_con.target = working_con.character_id
                    await session.commit()
                    total += 1
    logging.warning(f"Update Complete. {total} conditions updated")


def create_reminder_table():
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    db.MetaData()
    try:
        Base.metadata.create_all(engine)
        logging.warning("Creating Reminder Table")
    except Exception as e:
        logging.warning(e)
