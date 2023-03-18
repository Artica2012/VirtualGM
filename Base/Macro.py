import asyncio
import logging

import d20
import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_macro
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers, opposed_roll


class Macro:
    def __init__(self, ctx, engine, guild):
        self.ctx = ctx
        self.engine = engine
        self.guild = guild

    async def create_macro(self, character: str, macro_name: str, macro_string: str):
        logging.info(f"create_macro")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
            Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                result = await session.execute(
                    select(Macro).where(Macro.character_id == Character_Model.id).where(Macro.name == macro_name)
                )
                name_check = result.scalars().all()
                if len(name_check) > 0:
                    await self.ctx.channel.send(
                        "Duplicate Macro Name. Please use a different name or delete the old macro first"
                    )
                    return False

            async with session.begin():
                new_macro = Macro(character_id=Character_Model.id, name=macro_name, macro=macro_string)
                session.add(new_macro)
            await session.commit()
            await self.engine.dispose()
            return True
        except Exception as e:
            logging.error(f"create_macro: {e}")
            await self.engine.dispose()
            return False

    async def mass_add(self, character: str, data: str):
        logging.info(f"macro_mass_add")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
            Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                result = await session.execute(select(Macro.name).where(Macro.character_id == Character_Model.id))
                macro_list = result.scalars().all()

            # Process data
            processed_data = data.split(";")
            # print(processed_data)
            error_list = []
            async with session.begin():
                for row in processed_data[:-1]:
                    await asyncio.sleep(0)
                    macro_split = row.split(",")
                    if macro_split[0].strip() in macro_list:
                        error_list.append(macro_split[0].strip())
                    else:
                        macro_list.append(macro_split[0].strip())
                        new_macro = Macro(
                            character_id=Character_Model.id, name=macro_split[0].strip(), macro=macro_split[1].strip()
                        )
                        session.add(new_macro)
            await session.commit()
            await self.engine.dispose()
            if len(error_list) > 0:
                await self.ctx.channel.send(f"Unable to add following macros due to duplicate names:\n{error_list}")
            return True
        except Exception as e:
            logging.error(f"mass_add: {e}")
            await self.engine.dispose()
            return False

    async def delete_macro(self, character: str, macro_name: str):
        logging.info(f"delete_macro")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Macro = await get_macro(self.ctx, self.engine)

        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Macro)
                    .where(Macro.character_id == Character_Model.id)
                    .where(Macro.name == macro_name.split(":")[0])
                )
                con = result.scalars().one()
                await session.delete(con)
                await session.commit()

            await self.engine.dispose()
            return True
        except Exception as e:
            logging.error(f"delete_macro: {e}")
            await self.engine.dispose()
            return False

    async def delete_macro_all(self, character: str):
        logging.info("delete_macro_all")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Macro = await get_macro(self.ctx, self.engine)
        try:
            async with async_session() as session:
                result = await session.execute(select(Macro).where(Macro.character_id == Character_Model.id))
                con = result.scalars().all()
            for row in con:
                await asyncio.sleep(0)
                async with async_session() as session:
                    await session.delete(row)
                    await session.commit()
            await self.engine.dispose()
            return True
        except Exception as e:
            logging.error(f"delete_macro: {e}")
            await self.engine.dispose()
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
            macro_data = macro_list[0]
            await self.ctx.channel.send(
                "Error: Duplicate Macros with the Same Name. Rolling one macro, but please ensure that you do not have"
                " duplicate names."
            )
        dice_result = d20.roll(f"({macro_data.macro}){ParseModifiers(modifier)}")
        roll_str = opposed_roll(dice_result, d20.roll(f"{dc}")) if dc else dice_result
        output_string = f"{character}:\n{macro_name.split(':')[0]}\n{roll_str}"

        return output_string

    async def get_macro(self, character: str, macro_name: str):
        logging.info(f"get_macro {character}, {macro_name}")
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
            macro_data = macro_list[0]
            await self.ctx.channel.send(
                "Error: Duplicate Macros with the Same Name. Rolling one macro, but please ensure that you do not have"
                " duplicate names."
            )
        return macro_data.macro

    async def show(self, character):
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)

        async with async_session() as session:
            result = await session.execute(
                select(Macro).where(Macro.character_id == Character_Model.id).order_by(Macro.name.asc())
            )
            macro_list = result.scalars().all()

            view = discord.ui.View(timeout=None)
            for row in macro_list:
                await asyncio.sleep(0)
                button = self.MacroButton(self.ctx, self.engine, Character_Model, row)
                if len(view.children) == 24:
                    await self.ctx.send_followup(f"{character.name}: Macros", view=view, ephemeral=True)
                    view.clear_items()
                view.add_item(button)
            return view

    class MacroButton(discord.ui.Button):
        def __init__(self, ctx: discord.ApplicationContext, engine, character, macro):
            self.ctx = ctx
            self.engine = engine
            self.character = character
            self.macro = macro
            super().__init__(
                label=f"{macro.name}: {macro.macro}",
                style=discord.ButtonStyle.primary,
                custom_id=str(f"{character.id}_{macro.id}"),
            )

        async def callback(self, interaction: discord.Interaction):
            dice_result = d20.roll(self.macro.macro)
            output_string = f"{self.character.char_name}:\n{self.macro.name.split(':')[0]}\n{dice_result}"

            await interaction.response.send_message(output_string)
