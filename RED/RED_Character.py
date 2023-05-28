import asyncio
import logging

import discord
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import database_operations
from Base.Character import Character
from database_models import get_tracker, get_condition, get_RED_tracker
from utils.utils import get_guild

default_pic = (
    "https://cdn.discordapp.com/attachments/1106097168181375066/1111774244808949760/artica"
    "_A_portrait_of_a_genetic_cyberpunk_character._Cloaked_in__7108cd00-9880-4d22-9d18-c0930eb9a149.png"
)


async def get_RED_Character(char_name, ctx, guild=None, engine=None):
    if engine is None:
        engine = database_operations.engine
    guild = await get_guild(ctx, guild)
    RED_tracker = await get_tracker(ctx, engine, id=guild.id)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(RED_tracker).where(func.lower(RED_tracker.name) == char_name.lower()))
            character = result.scalars().one()
            return RED_Character(char_name, ctx, engine, character, guild=guild)

    except NoResultFound:
        return None


class RED_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, guild=None):
        super().__init__(char_name, ctx, engine, character)
        self.level = character.level
        self.humanity = character.humanity
        self.current_luck = character.current_luck
        self.stats = character.stats
        self.skills = character.skills
        self.attacks = character.attacks
        self.armor = character.armor
        self.cyber = character.cyber
        self.net = character.net
        self.macros = character.macros
        self.bonuses = character.bonuses

    async def update(self):
        logging.info(f"Updating character: {self.char_name}")
        await calculate(self.ctx, self.engine, self.char_name, guild=self.guild)
        self.character_model = await self.character()
        self.char_name = self.character_model.name
        self.id = self.character_model.id
        self.name = self.character_model.name
        self.player = self.character_model.player
        self.user = self.character_model.user
        self.current_hp = self.character_model.current_hp
        self.max_hp = self.character_model.max_hp
        self.temp_hp = self.character_model.max_hp
        self.init_string = self.character_model.init_string
        self.init = self.character_model.init
        self.pic = self.character_model.pic if self.character_model.pic is not None else default_pic

        self.level = self.character_model.level
        self.humanity = self.character_model.humanity
        self.current_luck = self.character_model.current_luck
        self.stats = self.character_model.stats
        self.skills = self.character_model.skills
        self.attacks = self.character_model.attacks
        self.armor = self.character_model.armor
        self.cyber = self.character_model.cyber
        self.net = self.character_model.net
        self.macros = self.character_model.macros
        self.bonuses = self.character_model.bonuses


async def calculate(ctx, engine, char_name, guild=None):
    logging.info("Updating Character Model")
    guild = await get_guild(ctx, guild=guild)
    # Database boilerplate
    if guild is not None:
        RED_tracker = await get_RED_tracker(ctx, engine, id=guild.id)
    else:
        RED_tracker = await get_RED_tracker(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    bonuses, resistance = await parse_bonuses(ctx, engine, char_name, guild=guild)

    async with async_session() as session:
        try:
            query = await session.execute(select(RED_tracker).where(func.lower(RED_tracker.name) == char_name.lower()))
            character = query.scalars().one()

            stats = character.stats
            for stat in character.stats.keys():
                stats = await calc_stats(stat, stats, bonuses)
            character.stats = stats
            # print(stats)

            skills = character.skills
            # print(skills)
            for skill in character.skills.keys():
                # print(skill)
                skills = await calc_mods(stats, skill, skills, bonuses)
            character.skills = skills
            # print(skills)

            macros = []
            macros = character.attacks.keys()
            character.macros = macros

            await session.commit()

        except Exception as e:
            logging.error(e)


async def calc_stats(stat_name, stats, bonuses):
    stats[stat_name]["value"] = stats[stat_name]["base"] + await bonus_calc(stat_name, bonuses)
    return stats


async def calc_mods(stats: dict, skill_name: str, skills: dict, bonuses: dict):
    skill_base = skills[skill_name]["base"]
    stat = stats[skills[skill_name]["stat"]]["value"]
    skills[skill_name]["value"] = skill_base + stat + await bonus_calc(skill_name, bonuses)
    return skills


async def bonus_calc(skill, bonuses):
    mod = 0
    if skill in bonuses["pos"]:
        mod += bonuses["pos"][skill]
    if skill in bonuses["neg"]:
        mod -= bonuses["neg"][skill]
    return mod


async def parse_bonuses(ctx, engine, char_name: str, guild=None):
    guild = await get_guild(ctx, guild=guild)
    Character_Model = await get_RED_Character(char_name, ctx, guild=guild, engine=engine)
    # Database boilerplate
    if guild is not None:
        RED_tracker = await get_RED_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
    else:
        RED_tracker = await get_RED_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with async_session() as session:
            result = await session.execute(
                select(RED_tracker.id).where(func.lower(RED_tracker.name) == char_name.lower())
            )
            char = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(select(Condition).where(Condition.character_id == char))
            conditions = result.scalars().all()
    except NoResultFound:
        conditions = []

    bonuses = {"pos": {}, "neg": {}}
    resistances = {"resist": {}, "weak": {}, "immune": {}}

    for condition in conditions:
        await asyncio.sleep(0)
        # Get the data from the conditions
        # Write the bonuses into the two dictionaries

        data: str = condition.action
        data_list = data.split(",")
        for item in data_list:
            try:
                parsed = item.strip().split(" ")
                # Conditions adding conditions? Crazy

                item_name = ""
                specific_weapon = ""

                # print(parsed[0], parsed[0][0])
                if parsed[0][0] == '"':
                    # print("Opening Quote")
                    for x, item in enumerate(parsed):
                        # print(x, item)
                        # print(item[-1])
                        if item[-1] == '"':
                            item_name = " ".join(parsed[0 : x + 1])
                            item_name = item_name.strip('"')
                            parsed = parsed[x + 1 :]
                            break
                # print(item_name)
                # print(parsed)
                if item_name != "":
                    if item_name.title() in await Character_Model.attacks["list"]:
                        specific_weapon = f"{item_name},"
                    else:
                        parsed = []
                # print(specific_weapon)

                key = f"{specific_weapon}{parsed[0]}".lower()
                if parsed[1][1:] == "X":
                    value = int(condition.number)
                else:
                    try:
                        value = int(parsed[1][1:])
                    except ValueError:
                        value = int(parsed[1])

                if parsed[1][0] == "+":  # Positive
                    if key in bonuses["pos"]:
                        if value > bonuses["pos"][key]:
                            bonuses["pos"][key] = value
                    else:
                        bonuses["pos"][key] = value
                elif parsed[1][0] == "-":  # Negative
                    if key in bonuses["neg"]:
                        if value > bonuses["neg"][key]:
                            bonuses["neg"][key] = value
                    else:
                        bonuses["neg"][key] = value
            except Exception:
                pass

    # print(bonuses)
    # print(resistances)
    return bonuses, resistances
