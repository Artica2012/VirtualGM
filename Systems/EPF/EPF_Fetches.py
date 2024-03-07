from Systems.Base.API_Fetches import APIFetches
from Systems.EPF.EPF_Support import EPF_SKills


class EPFFetches(APIFetches):
    async def get_attributes(self, target):
        option_list = ["AC"]
        option_list.extend(EPF_SKills)
        return option_list
