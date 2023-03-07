import discord

class Automation():
    def __init__(self, ctx, engine, guild):
        self.ctx = ctx
        self.engine = engine
        self.guild = guild

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier):
        return "Attack Function not set up for current system."

    async def save(self, character, target, save, dc, modifier):
        return "Save Function not set up for current system."

