import asyncio
import logging

import d20
import discord

import EPF.EPF_Support
import PF2e.pf2_functions
from Base.Macro import Macro
from EPF.EPF_Character import get_EPF_Character, EPF_Character
from utils.Char_Getter import get_character


class EPF_Macro(Macro):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    def opposed_roll(self, roll: d20.RollResult, dc: d20.RollResult):
        # print(f"{roll} - {dc}")
        success_string = PF2e.pf2_functions.PF2_eval_succss(roll, dc)
        color = EPF.EPF_Support.EPF_Success_colors(success_string)
        return (
            (
                f"{':thumbsup:' if success_string == 'Critical Success' or success_string == 'Success' else ':thumbsdown:'} {roll} >="  # noqa
                f" {dc} {success_string}!"
            ),
            color,
        )

    async def roll_macro(self, character: str, macro_name: str, dc, modifier: str, guild=None):
        logging.info("EPF roll_macro")
        Character_Model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
        dice_result = await Character_Model.roll_macro(macro_name, modifier)
        if dice_result == 0:
            embed = await super().roll_macro(character, macro_name, dc, modifier, guild)
        else:
            roll_str = self.opposed_roll(dice_result, d20.roll(f"{dc}")) if dc else dice_result
            output_string = f"{roll_str[0]}"

            embed = discord.Embed(
                title=Character_Model.char_name,
                fields=[discord.EmbedField(name=macro_name, value=output_string)],
                color=roll_str[1],
            )
            embed.set_thumbnail(url=Character_Model.pic)

        return embed

    async def show(self, character):
        Character_Model = await get_EPF_Character(character, self.ctx, engine=self.engine, guild=self.guild)

        macro_list = await Character_Model.macro_list()

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
            Macro = EPF_Macro(self.ctx, self.engine, self.guild)
            output_string = await Macro.roll_macro(self.character.char_name, self.macro, None, "", guild=self.guild)

            await interaction.response.send_message(output_string)
