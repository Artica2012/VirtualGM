# exporter.py

import os

import sqlalchemy as db
from dotenv import load_dotenv
from sqlalchemy import inspect

from database_models import disease_table, feat_table, power_table, monster_table, item_table, ritual_table
from database_operations import get_db_engine

# define global variables

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


#######################################################################
#######################################################################
# Export function for each database table

def disease_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = disease_table(metadata)
    if not inspect(engine).has_table(emp):

        for row in data:
            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                # print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return


def feat_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = feat_table(metadata)
    if not inspect(engine).has_table(emp):
        metadata.create_all(engine)
        for row in data:
            # print(f"Type: {row['Type']}, ID: {row['ID']}, Title: {row['Title']}, URL: {row['URL']}")

            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                # print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return


def power_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = power_table(metadata)
    if not inspect(engine).has_table(emp):
        metadata.create_all(engine)
        for row in data:
            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                # print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return


def monster_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = monster_table(metadata)
    if not inspect(engine).has_table(emp):
        metadata.create_all(engine)
        for row in data:
            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return

def item_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = item_table(metadata)
    if not inspect(engine).has_table(emp):
        metadata.create_all(engine)
        for row in data:
            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    Category=row["Category"],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                # print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return

def ritual_export(data):
    engine = get_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=DATABASE)
    metadata = db.MetaData()
    emp = ritual_table(metadata)
    if not inspect(engine).has_table(emp):
        metadata.create_all(engine)
        for row in data:
            try:
                stmt = emp.insert().values(
                    Type=row['Type'],
                    ID=row["ID"],
                    Title=row['Title'],
                    URL=row['URL']
                )
                compiled = stmt.compile()
                with engine.connect() as conn:
                    result = conn.execute(stmt)
                # print(f"{row['Title']} Written")
            except Exception as e:
                print(e)
    return