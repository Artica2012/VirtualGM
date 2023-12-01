from Base.Utilities import Utilities


class STF_Utilities(Utilities):
    def __init__(self, ctx, guild, engine):
        super().__init__(ctx, guild, engine)

    async def add_character(self, bot, name: str, hp: int, player_bool: bool, init: str, image: str = None, **kwargs):
        await self.ctx.channel.send("Please use `/stf import_character` to add a character")
        return False

    async def copy_character(self, name: str, new_name: str):
        await self.ctx.channel.send("Please use `/stf import_character` to add a character")
        return False
