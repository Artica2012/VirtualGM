import asyncio
import logging

import d20
import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Macro import Macro
from EPF.EPF_Character import EPF_Character
from RED.RED_Character import get_RED_Character
from RED.RED_Support import RED_Roll_Result
from database_models import get_macro
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers
from utils.utils import relabel_roll


class RED_Macro(Macro):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def roll_macro(self, character: str, macro_name: str, dc, modifier: str, guild=None):
        logging.info("RED roll_macro")
        Character_Model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
        dice_result = RED_Roll_Result(await Character_Model.roll_macro(macro_name, modifier))

        if dice_result == 0:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            macro_table = await get_macro(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                result = await session.execute(
                    select(macro_table)
                    .where(macro_table.character_id == Character_Model.id)
                    .where(macro_table.name == macro_name.split(":")[0])
                )
            try:
                macro_data = result.scalars().one()
            except Exception:
                async with async_session() as session:
                    result = await session.execute(
                        select(macro_table)
                        .where(macro_table.character_id == Character_Model.id)
                        .where(macro_table.name == macro_name.split(":")[0])
                    )
                    macro_list = result.scalars().all()
                # print(macro_list)
                try:
                    macro_data = macro_list[0]
                except Exception:
                    embed = discord.Embed(
                        title=character,
                        fields=[
                            discord.EmbedField(
                                name=macro_name,
                                value=(
                                    "Error: Duplicate Macros with the Same Name or invalid macro. Rolling one macro,"
                                    " but please ensure that you do not have duplicate names."
                                ),
                            )
                        ],
                    )
                    return embed
            try:
                dice_result = RED_Roll_Result(d20.roll(f"({macro_data.macro}){ParseModifiers(modifier)}"))
            except Exception:
                dice_result = RED_Roll_Result(d20.roll(f"({relabel_roll(macro_data.macro)}){ParseModifiers(modifier)}"))
            if dc:
                roll_str = self.opposed_roll(dice_result, d20.roll(f"{dc}"))
                output_string = f"{roll_str[0]}"
                color = roll_str[1]
            else:
                output_string = str(dice_result)
                color = discord.Color.dark_grey()

        else:
            if dc != 0:
                roll_str = self.opposed_roll(dice_result, d20.roll(f"{dc}"))
                output_string = f"{roll_str[0]}"
                color = roll_str[1]
            else:
                output_string = str(dice_result)
                color = discord.Color.dark_grey()

        embed = discord.Embed(
            title=Character_Model.char_name,
            fields=[discord.EmbedField(name=macro_name, value=output_string)],
            color=color,
        )
        embed.set_thumbnail(url=Character_Model.pic)

        return embed

    async def show(self, character):
        Character_Model = await get_RED_Character(character, self.ctx, engine=self.engine, guild=self.guild)

        macro_list = Character_Model.macros

        view = discord.ui.View(timeout=None)
        for macro in macro_list:
            try:
                roll_string = await Character_Model.get_roll(macro)
                if roll_string == 0:
                    roll_string = await super().get_macro(character, macro, Character_Model=Character_Model)
                await asyncio.sleep(0)
                button = self.MacroButton(
                    self.ctx, self.engine, self.guild, Character_Model, macro, f"{macro}: {roll_string}"
                )
                if len(view.children) == 24:
                    await self.ctx.send_followup(f"{character.name}: Macros", view=view, ephemeral=True)
                    view.clear_items()
                view.add_item(button)
            except Exception as e:
                logging.error(f"{e} {macro}")
        return view

    class MacroButton(discord.ui.Button):
        def __init__(self, ctx: discord.ApplicationContext, engine, guild, character, macro, title):
            self.ctx = ctx
            self.engine = engine
            self.character: EPF_Character = character
            self.macro = macro
            self.guild = guild
            self.title = title
            super().__init__(
                label=f"{title}",
                style=discord.ButtonStyle.primary,
                custom_id=str(f"{character.id}_{macro}"),
            )

        async def callback(self, interaction: discord.Interaction):
            Macro = RED_Macro(self.ctx, self.engine, self.guild)
            output = await Macro.roll_macro(self.character.char_name, self.macro, 0, "", guild=self.guild)

            await interaction.response.send_message(embed=output)
