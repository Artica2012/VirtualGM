# database_operations.py
import datetime
import json
import logging
import os

import sqlalchemy as db
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy import select

from Backend.Database.database_models import Global, Base, RollLogBase, Log
from Backend.Database.engine import engine, look_up_engine, async_session
from Backend.WS.WebsocketHandler import socket

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


# Get the engine
def get_asyncio_db_engine(user, password, host, port, db):
    if db == SERVER_DATA:
        return engine
    elif db == DATABASE:
        return look_up_engine
    else:
        return None


def get_db_engine(user, password, host, port, db):
    url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    engine = create_engine(url, pool_size=10, echo=False)
    return engine


async def update_global_manager():
    try:
        alter_string = text('ALTER TABLE "global_manager" ADD column "members" json')
        async with async_session() as session:
            await session.execute(alter_string)
            await session.commit()
    except Exception:
        logging.error("Unable to update Global Manager")


async def update_tracker_table():
    async with async_session() as session:
        result = await session.execute(select(Global))
        guild = result.scalars().all()

    for row in guild:
        try:
            # print(f"Updating {row.id}")
            alter_string = text(f'ALTER TABLE "Tracker_{row.id}" ADD variables JSON')
            async with async_session() as session:
                await session.execute(alter_string)
                await session.commit()
        except Exception as e:
            print(f"{row.id}, {e}")


async def update_con_table():
    total = 0
    async with async_session() as session:
        result = await session.execute(select(Global))
        guild = result.scalars().all()

    for row in guild:
        try:
            if row.system == "EPF" or row.system == "STF" or row.system == "RED":
                print(f"Updating {row.id}")
                alter_string = text(f'ALTER TABLE "Condition_{row.id}" ADD stable BOOLEAN')
                alter_string_2 = text(f'ALTER TABLE "Condition_{row.id}" ADD value INTEGER')
                alter_string_3 = text(f'ALTER TABLE "Condition_{row.id}" ADD eot_parse BOOLEAN')
                async with async_session() as session:
                    try:
                        await session.execute(alter_string)
                        await session.commit()
                    except Exception as e:
                        print("#1 fail", e)

                async with async_session() as session:
                    try:
                        await session.execute(alter_string_2)
                        await session.commit()
                    except Exception as e:
                        print("#2 fail", e)

                async with async_session() as session:
                    try:
                        await session.execute(alter_string_3)
                        await session.commit()
                    except Exception as e:
                        print("#3 fail", e)
                    # await session.commit()
        except Exception as e:
            print(f"{row.id}, {e}")

    logging.warning(f"Update Complete. {total} conditions updated")


def create_reminder_table():
    db.MetaData()
    try:
        Base.metadata.create_all(engine)
        logging.warning("Creating Reminder Table")
    except Exception as e:
        logging.warning(e)


def create_roll_log():
    db.MetaData()
    try:
        RollLogBase.metadata.create_all(engine)
        logging.warning("Creating Roll Log")
    except Exception as e:
        logging.warning(e)


def async_partial(async_func, *args):
    async def wrapped(async_func, *args):
        return await async_func(*args)

    return wrapped


async def log_roll(guild, character, message, secret=False):
    try:
        timestamp = int(datetime.datetime.utcnow().timestamp())
        async with async_session() as session:
            async with session.begin():
                log = Log(guild_id=guild, character=character, message=message, timestamp=timestamp, secret=secret)
                session.add(log)
            await session.commit()
        ws_output = json.dumps(
            {"guildID": guild, "character": character, "message": message, "timestamp": timestamp, "secret": secret}
        )
        await socket.stream(guild, ws_output, "log")

        return True
    except Exception as e:
        logging.error(f"log_roll: {e}")
        return False
