from Systems.Base.API_Fetches import APIFetches
from Systems.PF2e.pf2_functions import PF2_attributes, PF2_saves


class PF2Fetches(APIFetches):
    async def get_attributes(self, target):
        return PF2_attributes

    def set_attributes(self, target):
        return PF2_saves
