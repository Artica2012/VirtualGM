import d20
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_macro
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.parsing import ParseModifiers


class Automation:
    def __init__(self, ctx, engine, guild):
        self.ctx = ctx
        self.engine = engine
        self.guild = guild

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier):
        return "Attack Function not set up for current system."

    async def save(self, character, target, save, dc, modifier):
        return "Save Function not set up for current system."

    async def damage(self, bot, character, target, roll, modifier, healing):
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)
        Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)

        try:
            roll_result: d20.RollResult = d20.roll(f"({roll}){ParseModifiers(modifier)}")
            output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
        except Exception:
            try:
                async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                async with async_session() as session:
                    result = await session.execute(
                        select(Macro.macro).where(Macro.character_id == Character_Model.id).where(Macro.name == roll)
                    )
                    macro_roll = result.scalars().one()
                roll_result = d20.roll(f"({macro_roll}){ParseModifiers(modifier)}")
                output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
            except:  # Error handling in case that a non-macro string in input
                roll_result = d20.roll(0)
                output_string = "Error: Invalid Roll, Please try again."

        await Target_Model.change_hp(roll_result.total, healing)
        await Tracker_Model.update_pinned_tracker()
        return output_string

    async def auto(self, bot, character, target, attack):
        return "Auto Function not set up for current system"
