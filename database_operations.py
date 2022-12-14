# database_operations.py
import logging
import os

import sqlalchemy as db
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import select, inspect
# imports
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session

from database_models import Global, reminder_table, Base

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


# Get the engine
def get_asyncio_db_engine(user, password, host, port, db):
    url = f'postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}'
    # print(url)
    # if not database_exists(url):
    #     create_database(url)
    engine = create_async_engine(url, echo=False, pool_size=10, max_overflow=-1)
    return engine


def get_db_engine(user, password, host, port, db):
    url = f'postgresql://{user}:{password}@{host}:{port}/{db}'
    # print(url)
    # if not database_exists(url):
    #     create_database(url)
    engine = create_engine(url, pool_size=10, echo=False)
    return engine


def update_tracker_table():
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    with Session(engine) as session:
        guild = session.execute(select(Global)).all()
        for row in guild:
            print(row[0].id)
            alter_string = f'ALTER TABLE "Tracker_{row[0].id}" ADD init_string varchar(255)'
            with engine.connect() as conn:
                conn.execute(alter_string)


def update_con_table():
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    with Session(engine) as session:
        guild = session.execute(select(Global)).all()
        for row in guild:
            print(row[0].id)
            try:
                alter_string = f'ALTER TABLE "Condition_{row[0].id}" ADD flex boolean DEFAULT FALSE'
                with engine.connect() as conn:
                    conn.execute(alter_string)
            except Exception as e:
                print(f'Table {row[0].id} Not Updated')

def create_reminder_table():
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    metadata = db.MetaData()
    try:
        Base.metadata.create_all(engine)
        logging.warning("Creating Reminder Table")
    except Exception as e:
        logging.warning(e)
