from Systems.Base.API_Fetches import APIFetches
from Systems.EPF.EPF_Support import EPF_SKills
from Systems.PF2e.pf2_functions import PF2_saves


class EPFFetches(APIFetches):
    async def get_attributes(self, target):
        option_list = ["AC"]
        option_list.extend(EPF_SKills)
        return option_list

    def get_saves(self):
        return PF2_saves
