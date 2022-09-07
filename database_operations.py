#database_operations.py

# imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
import sqlite3
import os
from dotenv import load_dotenv

DATABASE = os.getenv("DATABASE")

def get_tracker_engine(user, password, host, port, db):
    url = f'postgresql://{user}:{str(password)}@{host}:{port}/{db}'
    if not database_exists(url):
        create_database(url)
    engine = create_engine(url, pool_size=50, echo=False)
    return engine



def create_connection(database):
    """ create a database connection to the SQLite database
            specified by the db_file
        :param db_file: database file
        :return: Connection object or None
        """
    conn = None
    try:
        conn = sqlite3.connect(f"{database}.db")
    except Exception as e:
        print(e)

    return conn

# Standard Database query for the 4e search
# May need updated if we switch off of Sqlite3
def query_database(conn, table, query):
    """
    Query tasks
    :param conn: the connection object
    :param table: the table to query
    :param query: name to query
    :return: query results
    """

    with conn:
        cur = conn.cursor()
        res = cur.execute(f"SELECT * FROM {table} WHERE Title LIKE '%{query}%' ORDER By ID")
        #Only return the first 10 results
        data = res.fetchmany(10)
    return data
