import d20
import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Bot import bot
from database_models import Global
from database_operations import engine
from utils.Char_Getter import get_character
from utils.Macro_Getter import get_macro_object
from utils.parsing import ParseModifiers
from utils.utils import direct_message


class AutoOutput:
    def __init__(self, embed: discord.Embed, raw: dict):
        self.embed = embed
        self.raw = raw


class Automation:
    def __init__(self, ctx, engine, guild):
        self.ctx = ctx
        self.engine = engine
        self.guild = guild

    async def gm_log(self, output_string, Target_Model):
        if self.guild.audit_log is None:
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            async with async_session() as session:
                result = await session.execute(select(Global).where(Global.id == self.guild.id))

                guild_result = result.scalars().one()

                guild_result.audit_log = "GM"
            await session.commit()

            self.guild = guild_result

        message = f"{output_string}. <{Target_Model.current_hp}/{Target_Model.max_hp}>"
        if "DM" in self.guild.audit_log:
            gm = bot.get_user(int(self.guild.gm))
            await direct_message(gm, message)

        if "GM" in self.guild.audit_log:
            gm_channel = bot.get_channel(int(self.guild.gm_tracker_channel))
            await gm_channel.send(message)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier, multi=False):
        return "Attack Function not set up for current system."

    async def save(self, character, target, save, dc, modifier):
        return "Save Function not set up for current system."

    async def damage(self, bot, character, target, roll, modifier, healing, damage_type: str, crit=False, multi=False):
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)

        try:
            roll_result: d20.RollResult = d20.roll(f"({roll}){ParseModifiers(modifier)}")
            if roll_result.total < 0:
                total = 0
            else:
                total = roll_result.total
            output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
        except Exception:
            try:
                Macro = await get_macro_object(self.ctx, self.engine, self.guild)
                macro_roll = await Macro.raw_macro(character, roll)
                # print(macro_roll)

                if crit:
                    roll_result = d20.roll(f"(({macro_roll}){ParseModifiers(modifier)})*2")
                else:
                    roll_result = d20.roll(f"({macro_roll}){ParseModifiers(modifier)}")

                if roll_result.total < 0:
                    total = 0
                else:
                    total = roll_result.total

                output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
            except Exception:  # Error handling in case that a non-macro string in input
                total = 0
                output_string = "Error: Invalid Roll, Please try again."

        raw_output = {
            "string": output_string,
            "success": "",
            "roll": str(roll_result.roll),
            "roll_total": int(roll_result.total),
        }

        embed = discord.Embed(
            title=f"{Character_Model.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=roll, value=output_string)],
        )
        embed.set_thumbnail(url=Character_Model.pic)

        await Target_Model.change_hp(total, healing, post=False)
        # if not multi:
        #     await Tracker_Model.update_pinned_tracker()
        await self.gm_log(output_string, Target_Model)
        return AutoOutput(embed=embed, raw=raw_output)

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
