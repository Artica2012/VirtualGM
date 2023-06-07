import asyncio
import logging

import d20
import discord
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import database_operations
from Base.Character import Character
from database_models import get_tracker, get_condition, get_RED_tracker, get_macro
from utils.parsing import ParseModifiers
from utils.utils import get_guild
from RED.RED_Support import RED_SKills, RED_Roll_Result, RED_AF_DV, RED_SS_DV

default_pic = (
    "https://cdn.discordapp.com/attachments/1106097168181375066/1111774244808949760/artica"
    "_A_portrait_of_a_genetic_cyberpunk_character._Cloaked_in__7108cd00-9880-4d22-9d18-c0930eb9a149.png"
)


async def get_RED_Character(char_name, ctx, guild=None, engine=None):
    if engine is None:
        engine = database_operations.engine
    guild = await get_guild(ctx, guild)
    print(guild.id)
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
        self.guild = guild
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

    async def get_roll(self, item: str):
        item = item.lower()
        # print(item)
        logging.info(f"RED returning roll: {item}")
        if item in self.skills.keys():
            return f"1d10+{self.skills[item]['value']}"
        elif item in self.attacks.keys():
            return await self.weapon_attack(item)
        elif item in RED_SKills.keys():
            return f"1d10+{await self.get_skill(item)}"
        else:
            try:
                async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                macro_table = await get_macro(self.ctx, self.engine, id=self.guild.id)
                async with async_session() as macro_session:
                    result = await macro_session.execute(
                        select(macro_table.macro)
                        .where(macro_table.character_id == self.id)
                        .where(func.lower(macro_table.name) == item)
                    )
                    return result.scalars().one()
            except NoResultFound:
                return "0"

    async def get_skill(self, item: str):
        item = item.lower()
        if item in self.skills.keys():
            print(self.skills[item]["value"])
            return self.skills[item]["value"]
        elif item in RED_SKills:
            print(self.stats[RED_SKills[item]]["value"])
            return self.stats[RED_SKills[item]]["value"]
        else:
            return 0

    async def get_stat(self, item: str):
        item = item.lower()
        if item in self.stats.keys():
            print(self.stats[item]["value"])
            return self.stats[item]["value"]
        else:
            return None

    async def roll_macro(self, macro, modifier):
        macro_string = await self.get_roll(macro)
        if macro_string == 0:
            return 0
        roll_string = f"{macro_string}{ParseModifiers(modifier)}"
        print(roll_string)
        dice_result = RED_Roll_Result(d20.roll(roll_string))
        return dice_result

    async def red_get_auto_dv(self, weapon, range: int, target, autofire=False):
        try:
            if weapon["type"] == "ranged" or weapon["type"] == "advanced":
                weapon_type = weapon["category"]
                if range <= 6:
                    range = 6
                elif range <= 12:
                    range = 12
                elif range <= 25:
                    range = 25
                elif range <= 50:
                    range = 50
                elif range <= 100:
                    range = 100
                elif range <= 200:
                    range = 200
                elif range <= 400:
                    range = 400
                elif range <= 800:
                    range = 800

                if autofire:
                    ranged_dv = RED_AF_DV[weapon_type][range]
                else:
                    ranged_dv = RED_SS_DV[weapon_type][range]
                if ranged_dv is None:
                    return None
                elif await target.get_stat("ref") >= 8:
                    dex_dv = f"1d10+{await target.get_stat('dex')}+{await target.get_skill('evasion')}"
                    average = 5 + await target.get_stat("dex") + await target.get_skill("evasion")
                    if average > ranged_dv:
                        return dex_dv
                    else:
                        return ranged_dv
                else:
                    return ranged_dv
            else:
                dv = f"1d10+{await target.get_stat('dex')}+{await target.get_skill('evasion')}"

                # dv = 10
                return dv
        except Exception:
            return None

    async def weapon_attack(self, item):
        item = item.lower()
        logging.info(f"RED weapon attack: {item}")
        weapon = self.attacks[item]
        match weapon["type"]:  # noqa
            case "melee":
                stat = self.stats["dex"]["value"]
            case "ranged":
                stat = self.stats["ref"]["value"]
            case _:
                stat = self.stats["ref"]["value"]

        if weapon["skill"] in self.skills.keys():
            skill = self.skills[weapon["skill"]]["value"]
        else:
            skill = 0

        attack_mod = int(stat) + skill
        bonus = await bonus_calc("attack", self.bonuses)

        return f"1d10+{attack_mod}{ParseModifiers(f'{bonus}')}"

    async def weapon_damage(self, item: str, modifier: str, iter: int = 1):
        item = item.lower()
        attk_list = []
        for i in range(0, iter):
            attk_list.append(self.attacks[item]["dmg"])
        attk_string = "+".join(attk_list)
        dmg_str = f"{attk_string}{ParseModifiers(modifier)}"
        # print(dmg_str)
        dmg = RED_Roll_Result(d20.roll(dmg_str))
        return dmg

    async def get_weapon(self, item):
        item = item.lower()
        logging.info(f"RED get weapon: {item}")
        return self.attacks[item]

    async def ablate_armor(self, amount: int, location: str, reset=False):
        try:
            RED_tracker = await get_RED_tracker(self.ctx, self.engine, id=self.guild.id)
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            armor = self.armor
            if reset:
                for location in armor.keys():
                    try:
                        armor[location]["sp"] = armor[location]["base"]
                    except KeyError:
                        pass
            else:
                sp = armor[location]["sp"]
                print("sp: ", sp)
                new_sp = sp - amount
                if new_sp < 0:
                    new_sp = 0
                armor[location]["sp"] = new_sp
                print(armor)

            async with async_session() as session:
                query = await session.execute(select(RED_tracker).where(RED_tracker.id == self.id))
                character = query.scalars().one()
                character.armor = armor
                await session.commit()
            return True
        except Exception:
            return False

    async def damage_armor(self, amount: RED_Roll_Result, location: str):
        location = location.lower()
        try:
            print(amount.total, location)
            print(self.armor.keys())
            if "cover" in self.armor.keys():
                print("dmg_armor: cover")
                cover_hp = int(self.armor["cover"]["sp"])
                print(cover_hp, amount.total)
                if cover_hp > amount.total:
                    new_cover_hp = cover_hp - amount.total
                    await self.set_cover(new_cover_hp)
                    return 0
                else:
                    await self.set_cover(amount.total, remove=True)
                    return 0
            else:
                sp = self.armor[location]["sp"]
                print("Damage_Armor")
                print(sp, amount.total)
                if sp > amount.total:
                    return 0
                else:
                    dmg = amount.total - sp
                    await self.ablate_armor(1, location)
                    await self.change_hp(dmg, False, False)
                    await self.update()
                    return int(dmg)
        except Exception as e:
            print(e)
            return 0

    @property
    def armor_output_string(self):
        try:
            body = int(self.armor["body"]["sp"])
            head = int(self.armor["head"]["sp"])
            output_string = f"B:{body} SP/ H:{head} SP\n"
            # print(self.armor.keys())
            if "cover" in self.armor.keys():
                # print("COVER!!!!!!!!!!!!!!!!!!")
                cover = int(self.armor["cover"]["sp"])
                output_string += f"   Cover:{cover}\n"
            return output_string
        except Exception:
            return "ERROR!!!"

    async def set_cover(self, amount, remove=False):
        try:
            # print("set_armor")
            amount = int(amount)
            RED_tracker = await get_RED_tracker(self.ctx, self.engine, id=self.guild.id)
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            async with async_session() as session:
                query = await session.execute(select(RED_tracker).where(RED_tracker.id == self.id))
                character = query.scalars().one()
                # print(character.armor.keys())

                new_armor = character.armor.copy()
                if "cover" in character.armor.keys():
                    # print("cover")
                    if remove:
                        new_armor.pop("cover")
                    else:
                        new_armor["cover"] = {"sp": amount, "base": amount}
                else:
                    new_armor["cover"] = {"sp": amount, "base": amount}
                # print(new_armor)
                character.armor = new_armor
                await session.commit()
            await self.update()
            return True
        except Exception:
            return False


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
    try:
        async with async_session() as session:
            query = await session.execute(select(RED_tracker).where(func.lower(RED_tracker.name) == char_name.lower()))
            character = query.scalars().one()

            character.bonuses = bonuses
            character.resistances = resistance

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
            macros.extend(character.skills.keys())
            macros.extend(character.attacks.keys())
            macro_table = await get_macro(ctx, engine, id=guild.id)
            async with async_session() as macro_session:
                result = await macro_session.execute(
                    select(macro_table.name).where(macro_table.character_id == character.id)
                )
                macro_data = result.scalars().all()
            macros.extend(macro_data)
            print(macros)
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
    print(bonuses)
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
