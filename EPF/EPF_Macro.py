import asyncio
import logging

import d20
import discord
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Macro import Macro
from EPF.EPF_Character import get_EPF_Character, EPF_Character
from database_operations import get_asyncio_db_engine
from utils.Char_Getter import get_character
from utils.parsing import opposed_roll


class EPF_Macro(Macro):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def roll_macro(self, character: str, macro_name: str, dc,modifier: str, guild=None):
        logging.info("EPF roll_macro")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)


        logging.info("EPF")
        Character_Model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
        dice_result = await Character_Model.roll_macro(macro_name, modifier)
        roll_str = opposed_roll(dice_result, d20.roll(f"{dc}")) if dc else dice_result
        output_string = f"{character}:\n{macro_name}\n{roll_str}"

        return output_string

    async def show(self, character):
        Character_Model = await get_EPF_Character(character, self.ctx, engine=self.engine, guild=self.guild)

        macro_list = await Character_Model.macro_list()

        view = discord.ui.View(timeout=None)
        for macro in macro_list:
            await asyncio.sleep(0)
            button = self.MacroButton(self.ctx, self.engine, Character_Model, macro)
            if len(view.children) == 24:
                await self.ctx.send_followup(f"{character.name}: Macros", view=view, ephemeral=True)
                view.clear_items()
            view.add_item(button)
        return view

    class MacroButton(discord.ui.Button):
        def __init__(self, ctx: discord.ApplicationContext, engine, character, macro):
            self.ctx = ctx
            self.engine = engine
            self.character: EPF_Character  = character
            self.macro = macro
            super().__init__(
                label=f"{macro}",
                style=discord.ButtonStyle.primary,
                custom_id=str(f"{character.id}_{macro}"),
            )

        async def callback(self, interaction: discord.Interaction):
            dice_result = await self.character.roll_macro(self.macro, "")
            output_string = f"{self.character.char_name}:\n{self.macro}\n{dice_result}"

            await interaction.response.send_message(output_string)