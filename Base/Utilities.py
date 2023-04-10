import asyncio
import logging

import d20
from sqlalchemy import select, false
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_tracker, get_condition, get_macro
from error_handling_reporting import error_not_initialized, ErrorReport


class Utilities:
    def __init__(self, ctx, guild, engine):
        self.ctx = ctx
        self.guild = guild
        self.engine = engine

    async def add_character(self, bot, name: str, hp: int, player_bool: bool, init: str):
        logging.info("add_character")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

            initiative = 0
            if self.guild.initiative is not None:
                try:
                    roll = d20.roll(init)
                    initiative = roll.total
                except ValueError:
                    await self.ctx.channel.send(f"Invalid Initiative String `{init}`, Please check and try again.")
                    return False
                except Exception:
                    initiative = 0

            async with async_session() as session:
                Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
                async with session.begin():
                    tracker = Tracker(
                        name=name,
                        init_string=init,
                        init=initiative,
                        player=player_bool,
                        user=self.ctx.user.id,
                        current_hp=hp,
                        max_hp=hp,
                        temp_hp=0,
                    )
                    session.add(tracker)
                await session.commit()

            return True
        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"add_character: {e}")
            report = ErrorReport(self.ctx, "add_character", e, bot)
            await report.report()
            return False

    async def copy_character(self, name: str, new_name: str):
        logging.info("copy_character")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
            Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)

            # Load up the old character
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == name))
                character = char_result.scalars().one()

            # If initiative is active, roll initiative
            initiative = 0
            if self.guild.initiative is not None:
                try:
                    roll = d20.roll(character.init_string)
                    initiative = roll.total
                except Exception:
                    initiative = 0

            # Copy the character over into a new character with a new name
            async with session.begin():
                new_char = Tracker(
                    name=new_name,
                    init_string=character.init_string,
                    init=initiative,
                    player=character.player,
                    user=character.user,
                    current_hp=character.current_hp,
                    max_hp=character.max_hp,
                    temp_hp=character.temp_hp,
                )
                session.add(new_char)
            await session.commit()

            # Load the new character from the database, to get its ID
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == new_name))
                new_character = char_result.scalars().one()

            # Copy conditions
            async with async_session() as session:
                con_result = await session.execute(
                    select(Condition).where(Condition.character_id == character.id).where(Condition.visible == false())
                )
                conditions = con_result.scalars().all()

            async with session.begin():
                for condit in conditions:
                    await asyncio.sleep(0)
                    new_condition = Condition(
                        character_id=new_character.id,
                        counter=condit.counter,
                        title=condit.title,
                        number=condit.number,
                        auto_increment=condit.auto_increment,
                        time=condit.time,
                        visible=condit.visible,
                    )
                    session.add(new_condition)
                await session.commit()

            # Copy Macros
            async with async_session() as session:
                macro_result = await session.execute(select(Macro).where(Macro.character_id == character.id))
                macros = macro_result.scalars().all()

            async with session.begin():
                for mac in macros:
                    await asyncio.sleep(0)
                    new_macro = Macro(character_id=new_character.id, name=mac.name, macro=mac.macro)
                    session.add(new_macro)
                await session.commit()

            return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"copy_character: {e}")
            return False

    async def delete_character(self, character: str):
        logging.info("delete_Character")
        try:
            # load tables
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
            Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                # print(character)
                result = await session.execute(select(Tracker).where(Tracker.name == character))
                char = result.scalars().one()
                # print(char.id)
                result = await session.execute(select(Condition).where(Condition.character_id == char.id))
                Condition_list = result.scalars().all()
                # print(Condition_list)
                result = await session.execute(select(Macro).where(Macro.character_id == char.id))
                Macro_list = result.scalars().all()
            # Delete Conditions
            for con in Condition_list:
                await asyncio.sleep(0)
                async with async_session() as session:
                    await session.delete(con)
                    await session.commit()
            # Delete Macros
            for mac in Macro_list:
                await asyncio.sleep(0)
                async with async_session() as session:
                    await session.delete(mac)
                    await session.commit()
            # Delete the Character
            async with async_session() as session:
                await session.delete(char)
                await session.commit()
            await self.ctx.channel.send(f"{char.name} Deleted")
            return True
        except Exception as e:
            logging.warning(f"delete_character: {e}")
            return False

    async def edit_attack(self, character, attack, dmg_stat, attk_stat, crit, dmg, prof):
        await self.ctx.channel.send("Command Disabled for current system")
        return False

    async def edit_resistances(self, character, element, resist_weak, ammount):
        await self.ctx.channel.send("Command Disabled for current system")
        return False
