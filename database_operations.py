# database_operations.py

# imports
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database


# Get the engine
def get_db_engine(user, password, host, port, db):
    url = f'postgresql://{user}:{password}@{host}:{port}/{db}'
    # print(url)
    if not database_exists(url):
        create_database(url)
    engine = create_engine(url, pool_size=50, echo=False)
    return engine
