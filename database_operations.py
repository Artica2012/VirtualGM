# database_operations.py

# imports
from sqlalchemy import create_engine
import sqlalchemy as db
from sqlalchemy_utils import database_exists, create_database
from database_models import ConditionTable, TrackerTable, MacroTable, Global
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

import os
from dotenv import load_dotenv

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
def get_db_engine(user, password, host, port, db):
    url = f'postgresql://{user}:{password}@{host}:{port}/{db}'
    # print(url)
    if not database_exists(url):
        create_database(url)
    engine = create_engine(url, pool_size=50, echo=False)
    return engine


def update_tracker_table():
    metadata = db.MetaData()
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)

    with Session(engine) as session:
        guild = session.execute(select(Global)).all()
        for row in guild:
            print(row[0].id)
            alter_string = f'ALTER TABLE "Tracker_{row[0].id}" ADD init_string varchar(255)'
            with engine.connect() as conn:
                conn.execute(alter_string)


