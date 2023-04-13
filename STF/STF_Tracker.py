from Base.Tracker import Tracker
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.utils import get_guild


async def get_STF_Tracker(ctx, engine, init_list, bot, guild=None):
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    return STF_Tracker(ctx, engine, init_list, bot, guild=guild)


class STF_Tracker(Tracker):
    def __init__(self, ctx, engine, init_list, bot, guild=None):
        super().__init__(ctx, engine, init_list, bot, guild)
