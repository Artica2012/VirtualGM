import pandas as pd
import json
import sqlite3

def export_to_sql(data, database):
    df = pd.DataFrame.from_records(data[0], index=data[1])
    conn = sqlite3.connect(f'../discordSlashBot/{database}.db')
    c = conn.cursor()
    try:
        df.to_sql(f"{data[2]}",conn)
        conn.commit()
    except:
        c.execute(f"DROP TABLE {data[2]}")
        df.to_sql(f"{data[2]}",conn)
        conn.commit()
    conn.close()

