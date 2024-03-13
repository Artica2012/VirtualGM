from Systems.Base.API_Fetches import APIFetches
from Systems.STF.STF_Support import STF_Saves


class STFFetches(APIFetches):
    async def get_attributes(self, target):
        return ["KAC", "EAC", "DC"]

    async def get_saves(self):
        return STF_Saves
