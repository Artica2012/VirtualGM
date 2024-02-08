# database_operations.py
import datetime
import json
import logging
import os
import asyncio
import websockets

import sqlalchemy as db
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy import select

# imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import Global, Base, RollLogBase, Log

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
look_up_engine = create_async_engine(
    lookup_url, echo=False, pool_size=10, max_overflow=-1, query_cache_size=150, pool_pre_ping=True
)


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
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        alter_string = text('ALTER TABLE "global_manager" ADD column "members" json')
        async with async_session() as session:
            await session.execute(alter_string)
            await session.commit()
    except Exception:
        logging.error("Unable to update Global Manager")


async def update_tracker_table():
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
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
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
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
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    db.MetaData()
    try:
        Base.metadata.create_all(engine)
        logging.warning("Creating Reminder Table")
    except Exception as e:
        logging.warning(e)


def create_roll_log():
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
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


class WebsocketHandler:
    def __init__(self):
        self.connections = set()
        self.library = {}

    async def handle(self, websocket):
        self.connections.add(websocket)
        await websocket.send("Connected")
        while True:
            try:
                async for message in websocket:
                    print(message)

                    match message[:3].lower():  # noqa
                        case "pin":
                            await self.ping(websocket)
                        case "con":
                            await self.register(websocket, message)
                        case "clo":
                            await self.disconnect(websocket)

                await websocket.wait_closed()
            finally:
                await self.disconnect(websocket)

    async def disconnect(self, websocket):
        del_list = []

        for g in self.library.keys():
            if websocket in self.library[g]:
                self.library[g].remove(websocket)
                if len(self.library[g]) == 0:
                    del_list.append(g)

        for g in del_list:
            del self.library[g]

        try:
            self.connections.remove(websocket)
        except KeyError:
            pass

    async def ping(self, websocket):
        timestamp = datetime.datetime.now()
        await websocket.send(f"Pong {timestamp}")

    async def register(self, websocket, message):
        try:
            guild_id = int(message.split(":")[1])
        except ValueError as e:
            logging.error(f"Value Error:websocket {message}{e}")
            return False
        except TypeError as e:
            logging.error(f"Type Error: websocket {message}{e}")
            return False
        except Exception as e:
            logging.error(f"Error: websocket {message}{e}")
            return False

        if guild_id in self.library.keys():
            self.library[guild_id].append(websocket)
        else:
            self.library[guild_id] = [websocket]

        await websocket.send(f"Connected to: {guild_id}")

    async def stream_channel(self, guild_id, tracker_data, header):
        processed_data = {"type": header, "data": tracker_data}

        output = json.dumps(processed_data)
        channel = self.library[guild_id]
        for ws in channel:
            try:
                await ws.send(output)
            except Exception as e:
                logging.error(f"Websocket stream_channel error: {e}")

    async def library_check(self, guild_id):
        if guild_id in self.library.keys():
            return True
        else:
            return False

    async def broadcast(self, message):
        websockets.broadcast(self.connections, str(message))

    async def stream(self, guild_id, message, header: str):
        try:
            if await self.library_check(guild_id):
                await socket.stream_channel(guild_id, message, header)
        except Exception as e:
            logging.error(f"websocket stream {e}")


socket = WebsocketHandler()


async def log_roll(guild, character, message, secret=False):
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        timestamp = int(datetime.datetime.utcnow().timestamp())
        print(timestamp)
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
