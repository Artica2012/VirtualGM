#imports
import os.path
import parse


def connect_test(database):
    if not os.path.isfile(f'../discordSlashBot/{database}.db'):
        parse.parser(database)
        print("Database Created")
        return()
    else:
        print("Database Found")
        return()