import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")

url = f"postgresql+asyncpg://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{SERVER_DATA}"
engine = create_async_engine(url, echo=False, pool_size=20, max_overflow=-1)

lookup_url = f"postgresql+asyncpg://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}"
look_up_engine = create_async_engine(
    lookup_url, echo=False, pool_size=10, max_overflow=-1, query_cache_size=150, pool_pre_ping=True
)

async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
lookup_session = sessionmaker(look_up_engine, expire_on_commit=False, class_=AsyncSession)
