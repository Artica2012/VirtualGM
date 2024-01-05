import logging

import d20
import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Macro import Macro, macro_replace_vars, macro_vars_show
from database_models import get_tracker, get_macro
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers
from utils.utils import relabel_roll

default_vars = {"t": 5}


class D4e_Macro(Macro):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

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
                    "```\n"
                    "One or more variables found in error. Syntax is name=value, name=value\n"
                    "The variable 't' for trained is already automatically included."
                    "```"
                )

            return True

        except Exception as e:
            print(e)
            await self.ctx.channel.send(
                "```\n"
                "One or more variables found in error. Syntax is name=value, name=value\n"
                "The variable 't' for trained is already automatically included."
                "```"
            )
            return False

    async def show_vars(self, character):
        Character_Model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
        display_string = macro_vars_show(Character_Model.character_model.variables)

        embed = discord.Embed(
            title=Character_Model.char_name,
            fields=[discord.EmbedField(name="Variables", value=display_string)],
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=Character_Model.pic)

        return embed

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
