from Systems.Base.API_Fetches import APIFetches
from Systems.PF2e.pf2_functions import PF2_attributes


class PF2Fetches(APIFetches):
    async def get_attributes(self, target):
        return PF2_attributes
