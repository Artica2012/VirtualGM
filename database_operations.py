# imports
import sqlite3
import os
from dotenv import load_dotenv

DATABASE = os.getenv("DATABASE")


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

        data = res.fetchmany(20)
    return data
