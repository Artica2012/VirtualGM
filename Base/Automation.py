import d20
import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_macro
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers


class Automation:
    def __init__(self, ctx, engine, guild):
        self.ctx = ctx
        self.engine = engine
        self.guild = guild

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier, multi=False):
        return "Attack Function not set up for current system."

    async def save(self, character, target, save, dc, modifier):
        return "Save Function not set up for current system."

    async def damage(self, bot, character, target, roll, modifier, healing, damage_type: str, crit=False, multi=False):
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
                if crit:
                    roll_result = d20.roll(f"(({macro_roll}){ParseModifiers(modifier)})*2")
                else:
                    roll_result = d20.roll(f"({macro_roll}){ParseModifiers(modifier)}")
                output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
            except Exception:  # Error handling in case that a non-macro string in input
                roll_result = d20.roll(0)
                output_string = "Error: Invalid Roll, Please try again."

        embed = discord.Embed(
            title=f"{Character_Model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
        )
        embed.set_thumbnail(url=Character_Model.pic)

        await Target_Model.change_hp(roll_result.total, healing, post=False)
        # if not multi:
        #     await Tracker_Model.update_pinned_tracker()
        return embed

    async def auto(
        self,
        bot,
        character,
        target,
        attack,
        attack_modifier,
        target_modifier,
        dmg_modifier,
        dmg_type_override,
        multi=False,
    ):
        return "Auto Function not set up for current system"

    async def cast(
        self,
        bot,
        character,
        target,
        spell_name,
        level,
        attack_modifier,
        target_modifier,
        dmg_modifier,
        dmg_type_override,
        multi=False,
    ):
        return "Cast Function not set up for current system"
