import logging

import d20
import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Macro import Macro, macro_replace_vars
from PF2e.pf2_functions import PF2_eval_succss
from EPF.EPF_Support import EPF_Success_colors
from database_models import get_tracker, get_macro
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers
from utils.utils import relabel_roll

default_vars = {"u": 0, "t": 2, "e": 4, "m": 6, "l": 8}


class PF2_Macro(Macro):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    def opposed_roll(self, roll: d20.RollResult, dc: d20.RollResult):
        # print(f"{roll} - {dc}")
        success_string = PF2_eval_succss(roll, dc)
        color = EPF_Success_colors(success_string)
        return (
            (
                f"{':thumbsup:' if success_string == 'Critical Success' or success_string == 'Success' else ':thumbsdown:'} {roll} >="  # noqa
                f" {dc} {success_string}!"
            ),
            color,
        )

    async def set_vars(self, character, vars):
        try:
            print(vars)
            failure = False
            Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
            if Character_Model.character_model.variables is None:
                variables = {}
            else:
                try:
                    Character_Model.character_model.variables.keys()
                    variables = Character_Model.character_model.variables
                except Exception:
                    variables = {}

            var_list = vars.split(",")
            for item in var_list:
                try:
                    split = item.split("=")
                    variables[split[0].strip().lower()] = int(split[1])
                except Exception:
                    failure = True

            print(variables)

            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.id == Character_Model.id))
                char = result.scalars().one()
                print(char.variables)
                char.variables = variables

                await session.commit()

            if failure:
                await self.ctx.channel.send(
                    "```\nOne or more variables found in error. Syntax is name=value, name=value\nThe variables 'u, t,"
                    " e, m,l' for untrained, trained, expert, master, legendary are already automatically included.```"
                )

            return True

        except Exception as e:
            print(e)
            await self.ctx.channel.send(
                "```\nOne or more variables found in error. Syntax is name=value, name=value\nThe variables 'u, t, e,"
                " m,l' for untrained, trained, expert, master, legendary are already automatically included.```"
            )
            return False

    async def roll_macro(self, character: str, macro_name: str, dc, modifier: str, guild=None):
        logging.info(f"roll_macro {character}, {macro_name}")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)

        async with async_session() as session:
            result = await session.execute(
                select(Macro)
                .where(Macro.character_id == Character_Model.id)
                .where(Macro.name == macro_name.split(":")[0])
            )
        try:
            macro_data = result.scalars().one()
        except Exception:
            async with async_session() as session:
                result = await session.execute(
                    select(Macro)
                    .where(Macro.character_id == Character_Model.id)
                    .where(Macro.name == macro_name.split(":")[0])
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
                                "Error: Duplicate Macros with the Same Name or invalid macro. Rolling one macro, but"
                                " please ensure that you do not have duplicate names."
                            ),
                        )
                    ],
                )
                return embed
        try:
            dice_result = d20.roll(f"({macro_data.macro}){ParseModifiers(modifier)}")
        except Exception:
            try:
                dice_result = d20.roll(f"({relabel_roll(macro_data.macro)}){ParseModifiers(modifier)}")
            except Exception:
                raw_macro = macro_data.macro
                variables = Character_Model.character_model.variables
                replaced_macro = macro_replace_vars(raw_macro, variables, default_vars)

                dice_result = d20.roll(f"({replaced_macro}){ParseModifiers(modifier)}")

        if dc:
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
