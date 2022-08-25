import psycopg2
from configparser import ConfigParser


def config(filename='database.ini',section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)

    db = {}
    if parser.has_section((section)):
        params = parser.items((section))
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in the {filename} file')

    return db

def connect():
    """Connect to the PostgresSQL database server"""
    conn = None
    try:
        params = config()
        print ('Connecting to PostgresSQL database...')
        conn = psycopg2.connect(**params)
        #create server
        cur = conn.cursor()

        print ('PostgreSQL database version:')
        cur.execute('SELECT version()')
        db_version = cur.fetchone()
        print(db_version)
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed')

    if __name__ == '__main__':
        connect()
