import pandas as pd
import json
import sqlite3
import os
from dotenv import load_dotenv

import sqlalchemy as db
from sqlalchemy import create_engine, inspect
from database_models import Global, Base, tracker_table, condition_table
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from database_models import disease_table, feat_table, power_table

from database_operations import get_db_engine

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
        df.to_sql(f"{str(data[2])}", engine)
    except:
        print('Table Already Exits')

def disease_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = disease_table(metadata)
    if not inspect(engine).has_table(emp):
        metadata.create_all(engine)
        for row in data[0]:
            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    Level=row["Level"],
                    Source=row['Source'],
                    Data=row['Source'],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return

def feat_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = feat_table(metadata)
    if not inspect(engine).has_table(emp):
        metadata.create_all(engine)
        for row in data[0]:
            # print(f"Type: {row['Type']}, ID: {row['ID']}, Title: {row['Title']}, URL: {row['URL']}")

            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    Tier=row["Tier"],
                    Source=row['Source'],
                    Data=row['Source'],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return


def power_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = power_table(metadata)
    if not inspect(engine).has_table(emp):
        metadata.create_all(engine)
        for row in data[0]:
            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    Level=row["Level"],
                    Action=row['Action'],
                    Class=row['Class'],
                    Source=row['Source'],
                    Data=row['Source'],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return
