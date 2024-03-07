from Systems.Base.API_Fetches import APIFetches


class STFFetches(APIFetches):
    async def get_attributes(self, target):
        return ["KAC", "EAC", "DC"]
