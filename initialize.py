#initialize.py

# This file will contain any functions that should be run on bot startup

# imports
import os.path
import parse


# If the database is not found, parse a new one, if not, use the intact database.
def connect_test(database):
    if not os.path.isfile(f'../discordSlashBot/{database}.db'):
        parse.parser(database)
        print("Database Created")
        return
    else:
        print("Database Found")
        return
