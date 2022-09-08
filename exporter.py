import pandas as pd
import json
import sqlite3
import os
from dotenv import load_dotenv
import sqlalchemy
from database_operations import create_engine, get_db_engine

# define global variables
load_dotenv(verbose=True)
TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
DATABASE = os.getenv('DATABASE')
USERNAME = os.getenv('Username')
PASSWORD = os.getenv('Password')
HOSTNAME = os.getenv('Hostname')
PORT = os.getenv('PGPort')


def export_to_sql(data):
    df = pd.DataFrame.from_records(data[0], index=data[1])
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    try:
        df.to_sql(f"{data[2]}", engine)
    except:
        engine.execute(f"DROP TABLE {data[2]}")
        df.to_sql(f"{data[2]}",engine)
    engine.close()

