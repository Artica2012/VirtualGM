import asyncio
import datetime
import logging
from math import floor

import d20
import discord
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Character import Character
from STF.STF_Support import STF_Skills, STF_Conditions, STF_DMG_Types
from database_models import get_tracker, get_condition, get_macro
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from error_handling_reporting import error_not_initialized
from time_keeping_functions import get_time
from utils.parsing import ParseModifiers
from utils.utils import get_guild


async def get_STF_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating STF_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    tracker = await get_tracker(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(tracker).where(func.lower(tracker.name) == char_name.lower()))
            character = result.scalars().one()
        return STF_Character(char_name, ctx, engine, character, guild=guild)

    except NoResultFound:
        return None


class STF_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, guild):
        self.current_resolve = character.resolve
        self.max_resolve = character.max_resolve
        self.current_stamina = character.current_stamina
        self.max_stamina = character.max_stamina

        self.eac = character.eac
        self.kac = character.kac

        self.key_ability = character.key_ability

        self.str_mod = character.str_mod
        self.dex_mod = character.dex_mod
        self.con_mod = character.con_mod
        self.itl_mod = character.itl_mod
        self.wis_mod = character.wis_mod
        self.cha_mod = character.cha_mod

        self.fort_mod = character.fort_mod
        self.will_mod = character.will_mod
        self.reflex_mod = character.reflex_mod

        self.acrobatics_mod = character.acrobatics_mod
        self.athletics_mod = character.athletics_mod
        self.bluff_mod = character.bluff_mod
        self.computers_mod = character.computers_mod
        self.culture_mod = character.culture_mod
        self.diplomacy_mod = character.diplomacy_mod
        self.disguise_mod = character.disguise_mod
        self.engineering_mod = character.engineering_mod
        self.intimidate_mod = character.intimidate_mod
        self.life_science_mod = character.life_science_mod
        self.medicine_mod = character.medicine_mod
        self.mysticism_mod = character.mysticism_mod
        self.perception_mod = character.perception_mod
        self.physical_science_mod = character.physical_science_mod
        self.piloting_mod = character.piloting_mod
        self.sense_motive_mod = character.sense_motive_mod
        self.sleight_of_hand_mod = character.sleight_of_hand_mod
        self.stealth_mod = character.stealth_mod
        self.survival_mod = character.survival_mod

        self.eac = character.eac
        self.kac = character.kac

        self.macros = character.macros
        self.attacks = character.attacks
        self.spells = character.spells
        self.bonuses = character.bonuses
        self.resistance = character.resistance

        super().__init__(char_name, ctx, engine, character, guild)

    async def update(self):
        await calculate(self.ctx, self.engine, self.char_name, guild=self.guild)
        self.character_model = await self.character()
        self.id = self.character_model.id
        self.name = self.character_model.name
        self.player = self.character_model.player
        self.user = self.character_model.user
        self.current_hp = self.character_model.current_hp
        self.max_hp = self.character_model.max_hp
        self.temp_hp = self.character_model.max_hp
        self.init_string = self.character_model.init_string
        self.init = self.character_model.init

        self.current_resolve = self.character_model.resolve
        self.max_resolve = self.character_model.max_resolve
        self.current_stamina = self.character_model.current_stamina
        self.max_stamina = self.character_model.max_stamina

        self.eac = self.character_model.eac
        self.kac = self.character_model.kac

        self.key_ability = self.character_model.key_ability

        self.str_mod = self.character_model.str_mod
        self.dex_mod = self.character_model.dex_mod
        self.con_mod = self.character_model.con_mod
        self.itl_mod = self.character_model.itl_mod
        self.wis_mod = self.character_model.wis_mod
        self.cha_mod = self.character_model.cha_mod

        self.fort_mod = self.character_model.fort_mod
        self.will_mod = self.character_model.will_mod
        self.reflex_mod = self.character_model.reflex_mod

        self.acrobatics_mod = self.character_model.acrobatics_mod
        self.athletics_mod = self.character_model.athletics_mod
        self.bluff_mod = self.character_model.bluff_mod
        self.computers_mod = self.character_model.computers_mod
        self.culture_mod = self.character_model.culture_mod
        self.diplomacy_mod = self.character_model.diplomacy_mod
        self.disguise_mod = self.character_model.disguise_mod
        self.engineering_mod = self.character_model.engineering_mod
        self.intimidate_mod = self.character_model.intimidate_mod
        self.life_science_mod = self.character_model.life_science_mod
        self.medicine_mod = self.character_model.medicine_mod
        self.mysticism_mod = self.character_model.mysticism_mod
        self.perception_mod = self.character_model.perception_mod
        self.physical_science_mod = self.character_model.physical_science_mod
        self.piloting_mod = self.character_model.piloting_mod
        self.sense_motive_mod = self.character_model.sense_motive_mod
        self.sleight_of_hand_mod = self.character_model.sleight_of_hand_mod
        self.stealth_mod = self.character_model.stealth_mod
        self.survival_mod = self.character_model.survival_mod

        self.eac = self.character_model.eac
        self.kac = self.character_model.kac

        self.macros = self.character_model.macros
        self.attacks = self.character_model.attacks
        self.spells = self.character_model.spells
        self.bonuses = self.character_model.bonuses
        self.resistance = self.character_model.resistance

    async def set_stamina(self, amount: int):
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
            character = char_result.scalars().one()
            character.current_stamina = amount
            await session.commit()
            await self.update()

    async def set_resolve(self, amount: int):
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
            character = char_result.scalars().one()
            character.resolve = amount
            await session.commit()
            await self.update()

    async def change_hp(self, amount: int, heal: bool, post=True):
        logging.info("Edit HP")
        orig_ammount = amount
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
                character = char_result.scalars().one()

                if not heal:
                    # Handle Temp HP
                    if character.temp_hp > 0:
                        if amount > character.temp_hp:
                            amount = amount - character.temp_hp
                            character.temp_hp = 0
                        else:
                            character.temp_hp = character.temp_hp - amount
                            amount = 0

                    if character.current_stamina > 0 and character.current_stamina >= amount:
                        character.current_stamina = character.current_stamina - amount
                    elif character.current_stamina > 0:
                        difference = abs(character.current_stamina - amount)
                        character.current_hp = character.current_hp - difference
                        character.current_stamina = 0
                    else:
                        character.current_hp = character.current_hp - amount
                else:
                    character.current_hp = character.current_hp + amount
                    if character.current_hp > character.max_hp:
                        character.current_hp = character.max_hp

                await session.commit()
                await self.update()
            if post:
                if character.player:  # Show the HP it its a player
                    if heal:
                        await self.ctx.send_followup(
                            f"{self.name} healed for {amount}. New HP: {character.current_hp}/{character.max_hp}"
                        )
                    else:
                        await self.ctx.send_followup(
                            f"{self.name} damaged for {orig_ammount}. HP: {character.current_hp}/{character.max_hp}, "
                            f"SP: {character.current_stamina}/{character.max_stamina}"
                        )
                else:  # Obscure the HP if its an NPC
                    if heal:
                        await self.ctx.send_followup(f"{self.name} healed for {amount}. {await self.calculate_hp()}")
                    else:
                        await self.ctx.send_followup(
                            f"{self.name} damaged for {orig_ammount}. {await self.calculate_hp()}"
                        )
            return True
        except Exception as e:
            logging.warning(f"STF change_hp: {e}")
            return False

    async def restore_stamina(self):
        if self.current_stamina < self.max_stamina and self.current_resolve > 0:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
                character = char_result.scalars().one()
                character.current_stamina = character.max_stamina
                character.resolve -= 1
                await session.commit()
            await self.update()
            return True
        else:
            return False

    async def get_roll(self, item):
        logging.info(f"STF Returning roll: {item}")
        # print(item)
        if item == "Fortitude" or item == "Fort":
            return f"1d20+{self.fort_mod}"
        elif item == "Reflex":
            return f"1d20+{self.reflex_mod}"
        elif item == "Will":
            return f"1d20+{self.will_mod}"
        elif item == "Acrobatics":
            return f"1d20+{self.acrobatics_mod}"
        elif item == "Athletics":
            return f"1d20+{self.athletics_mod}"
        elif item == "BLuff":
            return f"1d20+{self.bluff_mod}"
        elif item == "Computers":
            return f"1d20+{self.computers_mod}"
        elif item == "Culture":
            return f"1d20+{self.culture_mod}"
        elif item == "Diplomacy":
            return f"1d20+{self.diplomacy_mod}"
        elif item == "Disguise":
            return f"1d20+{self.disguise_mod}"
        elif item == "Engineering":
            return f"1d20+{self.engineering_mod}"
        elif item == "Intimidate":
            return f"1d20+{self.intimidate_mod}"
        elif item == "Life Science":
            return f"1d20+{self.life_science_mod}"
        elif item == "Medicine":
            return f"1d20+{self.medicine_mod}"
        elif item == "Mysticism":
            return f"1d20+{self.mysticism_mod}"
        elif item == "Perception":
            return f"1d20+{self.perception_mod}"
        elif item == "Physical Science":
            return f"1d20+{self.physical_science_mod}"
        elif item == "Piloting":
            return f"1d20+{self.piloting_mod}"
        elif item == "Sense Motive":
            return f"1d20+{self.sense_motive_mod}"
        elif item == "Sleight of Hand":
            return f"1d20+{self.sleight_of_hand_mod}"
        elif item == "Stealth":
            return f"1d20+{self.stealth_mod}"
        elif item == "Survival":
            return f"1d20+{self.survival_mod}"
        else:
            try:
                # print(f"{item} - attk")
                return await self.weapon_attack(item)
            except KeyError:
                pass
            # Weapon Attack Code
            return 0

    async def weapon_attack(self, item):
        logging.info("weapon_attack")
        weapon = self.character_model.attacks[item]
        mod = weapon["attk_bonus"]
        bonus_mod = await skill_mod_calc("attack", 0, self.bonuses)
        return f"1d20{ParseModifiers(mod)}{ParseModifiers(bonus_mod)}"

    async def weapon_dmg(self, item, crit: bool = False, flat_bonus: str = ""):
        logging.info("weapon_dmg")
        weapon = self.character_model.attacks[item]
        print(weapon)

        bonus_mod = await skill_mod_calc("dmg", 0, self.bonuses)
        print(bonus_mod)
        return (
            f"{weapon['dmg_die_num']}{weapon['dmg_die']}{ParseModifiers(str(weapon['dmg_bonus']))}"
            f"{ParseModifiers(str(bonus_mod))}"
        )

    async def get_weapon(self, item):
        return self.attacks[item]

    async def get_dc(self, item):
        match item:  # noqa
            case "DC":
                match self.key_ability:  # noqa
                    case "str":
                        ka = self.str_mod
                    case "dex":
                        ka = self.dex_mod
                    case "con":
                        ka = self.con_mod
                    case "itl":
                        ka = self.itl_mod
                    case "wis":
                        ka = self.wis_mod
                    case "cha":
                        ka = self.cha_mod
                    case _:
                        ka = 0
                return 10 + floor(self.character_model.level / 2) + ka
            case "KAC":
                return self.kac
            case "EAC":
                return self.eac

    async def roll_macro(self, macro, modifier):
        macro_string = await self.get_roll(macro)
        if macro_string == 0:
            return 0
        roll_string = f"{macro_string}{ParseModifiers(modifier)}"
        # print(roll_string)
        dice_result = d20.roll(roll_string)
        return dice_result

    async def macro_list(self):
        list = self.character_model.macros.split(",")
        logging.info(list)
        if len(list) > 0:
            if list[-1] == "":
                return list[:-1]
            else:
                return list
        else:
            return []

    async def attack_list(self):
        list = []
        for key in self.character_model.attacks:
            list.append(key)
        return list

    async def set_cc(
        self,
        title: str,
        counter: bool,
        number: int,
        unit: str,
        auto_decrement: bool,
        flex: bool = False,
        data: str = "",
        visible: bool = True,
        update: bool = True,
    ):
        logging.info("set_cc")
        # Get the Character's data

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)

        # Check to make sure there isn't a condition with the same name on the character
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == self.id).where(Condition.title == title)
            )
            check_con = result.scalars().all()
            if len(check_con) > 0:
                return False

        # Process Data
        # print(data)
        if data == "":
            # print(title)
            if title in STF_Conditions.keys():
                data = STF_Conditions[title]
                # print(data)
        print(data)
        if "thp" in data:
            data_list = data.split(",")
            final_list = data_list.copy()
            for x, item in enumerate(data_list):
                parsed = item.strip().split(" ")
                if parsed[0].lower() == "thp":
                    try:
                        thp_num = int(parsed[1])
                        await self.add_thp(thp_num)
                        final_list.pop(x)
                    except Exception:
                        pass
            print(final_list)
            data = ", ".join(final_list)
            print(data)

        # Write the condition to the table
        try:
            if not self.guild.timekeeping or unit == "Round":  # If its not time based, then just write it
                # print(f"Writing Condition: {title}")
                async with session.begin():
                    condition = Condition(
                        character_id=self.id,
                        title=title,
                        number=number,
                        counter=counter,
                        auto_increment=auto_decrement,
                        time=False,
                        flex=flex,
                        action=data,
                        visible=visible,
                    )
                    session.add(condition)
                await session.commit()
                if update:
                    await self.update()
                return True

            else:  # If its time based, then calculate the end time, before writing it
                current_time = await get_time(self.ctx, self.engine)
                if unit == "Minute":
                    end_time = current_time + datetime.timedelta(minutes=number)
                elif unit == "Hour":
                    end_time = current_time + datetime.timedelta(hours=number)
                else:
                    end_time = current_time + datetime.timedelta(days=number)

                timestamp = end_time.timestamp()

                async with session.begin():
                    condition = Condition(
                        character_id=self.id,
                        title=title,
                        number=timestamp,
                        counter=counter,
                        auto_increment=True,
                        time=True,
                        action=data,
                        visible=visible,
                    )
                    session.add(condition)
                await session.commit()
                if update:
                    await self.update()
                return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"set_cc: {e}")
            return False

    # Delete CC
    async def delete_cc(self, condition):
        result = await super().delete_cc(condition)
        await self.update()
        return result

    async def update_resistance(self, weak, item, amount):
        Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
        try:
            updated_resistance = self.character_model.resistance
            # print(updated_resistance)
            if amount == 0:
                async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                async with async_session() as session:
                    query = await session.execute(select(Condition).where(func.lower(Condition.item) == item.lower()))
                    condition_object = query.scalars().one()
                    await session.delete(condition_object)
                    await session.commit()
                return True
            else:
                condition_string = f"{item} {weak} {amount};"
                result = await self.set_cc(item, True, amount, "Round", False, data=condition_string, visible=False)

            await self.update()
            # print(self.resistance)
            return True
        except Exception:
            return False


async def calculate(ctx, engine, char_name, guild=None):
    logging.info("Updating Character Model")
    guild = await get_guild(ctx, guild=guild)
    # Database boilerplate
    if guild is not None:
        STF_tracker = await get_tracker(ctx, engine, id=guild.id)
    else:
        STF_tracker = await get_tracker(ctx, engine)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    bonuses, resistance = await parse_bonuses(ctx, engine, char_name, guild=guild)

    async with async_session() as session:
        try:
            query = await session.execute(select(STF_tracker).where(STF_tracker.name == char_name))
            character = query.scalars().one()

            character.str_mod = await ability_mod_calc(character.str, "str", bonuses)
            character.dex_mod = await ability_mod_calc(character.dex, "dex", bonuses)
            character.con_mod = await ability_mod_calc(character.con, "con", bonuses)
            character.itl_mod = await ability_mod_calc(character.itl, "itl", bonuses)
            character.wis_mod = await ability_mod_calc(character.wis, "wis", bonuses)
            character.cha_mod = await ability_mod_calc(character.cha, "cha", bonuses)

            character.fort_mod = await save_mod_calc(character.con_mod, "fort", character.fort, bonuses)
            character.reflex_mod = await save_mod_calc(character.dex_mod, "reflex", character.reflex, bonuses)
            character.will_mod = await save_mod_calc(character.wis_mod, "will", character.will, bonuses)

            character.acrobatics_mod = await skill_mod_calc("acrobatics", character.acrobatics, bonuses)
            character.athletics_mod = await skill_mod_calc("athletics", character.athletics, bonuses)
            character.bluff_mod = await skill_mod_calc("bluff", character.bluff, bonuses)
            character.computers_mod = await skill_mod_calc("computers", character.computers, bonuses)
            character.culture_mod = await skill_mod_calc("culture", character.culture, bonuses)
            character.diplomacy_mod = await skill_mod_calc("diplomacy", character.diplomacy, bonuses)
            character.disguise_mod = await skill_mod_calc("disguise", character.disguise, bonuses)
            character.engineering_mod = await skill_mod_calc("engineering", character.engineering, bonuses)
            character.intimidate_mod = await skill_mod_calc("intimidate", character.intimidate, bonuses)
            character.life_science_mod = await skill_mod_calc("life_science", character.life_science, bonuses)
            character.medicine_mod = await skill_mod_calc("medicine", character.medicine, bonuses)
            character.mysticism_mod = await skill_mod_calc("mysticism", character.mysticism, bonuses)
            character.perception_mod = await skill_mod_calc("perception", character.perception, bonuses)
            character.physical_science_mod = await skill_mod_calc(
                "physical_science", character.physical_science, bonuses
            )
            character.piloting_mod = await skill_mod_calc("piloting", character.piloting, bonuses)
            character.sense_motive_mod = await skill_mod_calc("sense_motive", character.sense_motive, bonuses)
            character.sleight_of_hand_mod = await skill_mod_calc("sleight_of_hand", character.sleight_of_hand, bonuses)
            character.stealth_mod = await skill_mod_calc("stealth", character.stealth, bonuses)
            character.survival_mod = await skill_mod_calc("survival", character.survival, bonuses)

            character.eac = await skill_mod_calc("eac", character.base_eac, bonuses)
            character.kac = await skill_mod_calc("kac", character.base_kac, bonuses)

            if character.max_stamina != 0:
                character.init_string = f"1d20+{await skill_mod_calc('init', character.dex_mod, bonuses)}"
            character.bonuses = bonuses
            character.resistance = resistance

            macros = []
            for item in character.attacks.keys():
                # print(item)
                macros.append(item)
            # for item in character.spells.keys():
            #     macros.append(f"Spell Attack: {item['name']}")
            macros.extend(STF_Skills)

            Macro = await get_macro(ctx, engine, id=guild.id)
            async with async_session() as macro_session:
                result = await macro_session.execute(select(Macro.name).where(Macro.character_id == character.id))
                macro_list = result.scalars().all()
            macros.extend(macro_list)

            macro_string = ""
            for item in macros:
                macro_string += f"{item},"
            character.macros = macro_string

            await session.commit()

        except Exception as e:
            logging.warning(f"stf calculate: {e}")


async def ability_mod_calc(base: int, item: str, bonuses):
    mod = floor((base - 10) / 2)
    if item in bonuses["ability"]:
        mod += bonuses["ability"][item]
    if item in bonuses["armor"]:
        mod += bonuses["armor"][item]
    if item in bonuses["circumstance"]:
        mod += bonuses["circumstance"][item]
    if item in bonuses["divine"]:
        mod += bonuses["divine"][item]
    if item in bonuses["enhancement"]:
        mod += bonuses["enhancement"][item]
    if item in bonuses["insight"]:
        mod += bonuses["insight"][item]
    if item in bonuses["luck"]:
        mod += bonuses["luck"][item]
    if item in bonuses["morale"]:
        mod += bonuses["morale"][item]
    if item in bonuses["penalty"]:
        mod -= bonuses["penalty"][item]

    return mod


async def save_mod_calc(stat_mod, item: str, base_save, bonuses):
    mod = base_save

    if item in bonuses["ability"]:
        mod += bonuses["ability"][item]
    if item in bonuses["armor"]:
        mod += bonuses["armor"][item]
    if item in bonuses["circumstance"]:
        mod += bonuses["circumstance"][item]
    if item in bonuses["divine"]:
        mod += bonuses["divine"][item]
    if item in bonuses["enhancement"]:
        mod += bonuses["enhancement"][item]
    if item in bonuses["insight"]:
        mod += bonuses["insight"][item]
    if item in bonuses["luck"]:
        mod += bonuses["luck"][item]
    if item in bonuses["morale"]:
        mod += bonuses["morale"][item]
    if item in bonuses["penalty"]:
        mod -= bonuses["penalty"][item]

    return mod


async def skill_mod_calc(item: str, base_save, bonuses):
    mod = base_save

    if item in bonuses["ability"]:
        mod += bonuses["ability"][item]
    if item in bonuses["armor"]:
        mod += bonuses["armor"][item]
    if item in bonuses["circumstance"]:
        mod += bonuses["circumstance"][item]
    if item in bonuses["divine"]:
        mod += bonuses["divine"][item]
    if item in bonuses["enhancement"]:
        mod += bonuses["enhancement"][item]
    if item in bonuses["insight"]:
        mod += bonuses["insight"][item]
    if item in bonuses["luck"]:
        mod += bonuses["luck"][item]
    if item in bonuses["morale"]:
        mod += bonuses["morale"][item]
    if item in bonuses["penalty"]:
        mod -= bonuses["penalty"][item]

    return mod


async def parse_bonuses(ctx, engine, char_name: str, guild=None):
    guild = await get_guild(ctx, guild=guild)
    # Character_Model = await get_STF_Character(char_name, ctx, guild=guild, engine=engine)
    # Database boilerplate
    if guild is not None:
        STF_tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
    else:
        STF_tracker = await get_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with async_session() as session:
            result = await session.execute(select(STF_tracker.id).where(STF_tracker.name == char_name))
            char = result.scalars().one()

        async with async_session() as session:
            result = await session.execute(select(Condition).where(Condition.character_id == char))
            conditions = result.scalars().all()
    except NoResultFound:
        conditions = []

    bonuses = {
        "ability": {},
        "armor": {},
        "circumstance": {},
        "divine": {},
        "enhancement": {},
        "insight": {},
        "luck": {},
        "morale": {},
        "penalty": {},
    }
    resistances = {"resist": {}, "weak": {}, "immune": {}}

    # Obviously a temporary bypass
    # return bonuses, resistances

    # print("!!!!!!!!!!!!!!!!!!!111")
    # print(len(conditions))
    for condition in conditions:
        # print(f"{condition.title}, {condition.number}, {condition.action}")
        await asyncio.sleep(0)
        # Get the data from the conditions
        # Write the bonuses into the two dictionaries
        print(f"{condition.title}, {condition.action}")

        data: str = condition.action
        data_list = data.split(",")
        for item in data_list:
            try:
                parsed = item.strip().split(" ")

                if parsed[0].title() in STF_DMG_Types:
                    # print(True)
                    # print("Condition")
                    # print(f"0: {parsed[0]}, 1: {parsed[1]}, 2: {parsed[2]}")
                    if parsed[2][-1] == ";":
                        parsed[2] = parsed[2][:-1]
                    parsed[0] = parsed[0].lower()
                    match parsed[1]:
                        case "r":
                            resistances["resist"][parsed[0]] = int(parsed[2])
                        case "w":
                            resistances["weak"][parsed[0]] = int(parsed[2])
                        case "i":
                            resistances["immune"][parsed[0]] = 1

                key = parsed[0]
                if parsed[1][1:] == "X":
                    value = int(condition.number)
                else:
                    try:
                        value = int(parsed[1][1:])
                    except ValueError:
                        value = int(parsed[1])

                if parsed[1][0] == "-":
                    if key in bonuses["penalty"]:
                        if value > bonuses["penalty"][key]:
                            bonuses["penalty"][key] = value
                    else:
                        bonuses["penalty"][key] = value
                elif parsed[2] == "a":
                    if key in bonuses["ability"]:
                        if value > bonuses["ability"][key]:
                            bonuses["ability"][key] = value
                    else:
                        bonuses["ability"][key] = value
                elif parsed[2] == "r":
                    if key in bonuses["armor"]:
                        if value > bonuses["armor"][key]:
                            bonuses["armor"][key] = value
                    else:
                        bonuses["armor"][key] = value
                        # print(f"{key}: {bonuses['status_neg'][key]}")
                elif parsed[2] == "c":
                    if key in bonuses["circumstance"]:
                        if value > bonuses["circumstance"][key]:
                            bonuses["circumstance"][key] = value
                    else:
                        bonuses["circumstance"][key] = value
                elif parsed[2] == "d":
                    if key in bonuses["divine"]:
                        if value > bonuses["divine"][key]:
                            bonuses["divine"][key] = value
                    else:
                        bonuses["divine"][key] = value
                        # print(f"{key}: {bonuses['circumstances_neg'][key]}")
                elif parsed[2] == "e":  # Enhancement
                    if key in bonuses["enhancement"]:
                        if value > bonuses["enhancement"][key]:
                            bonuses["enhancement"][key] = value
                    else:
                        bonuses["enhancement"][key] = value
                        # print(f"{key}: {bonuses['item_pos'][key]}")
                elif parsed[2] == "i":
                    if key in bonuses["insight"]:
                        if value > bonuses["insight"][key]:
                            bonuses["insight"][key] = value
                    else:
                        bonuses["insight"][key] = value
                elif parsed[2] == "l":
                    if key in bonuses["luck"]:
                        if value > bonuses["luck"][key]:
                            bonuses["luck"][key] = value
                    else:
                        bonuses["luck"][key] = value
                elif parsed[2] == "m":
                    if key in bonuses["morale"]:
                        if value > bonuses["morale"][key]:
                            bonuses["morale"][key] = value
                    else:
                        bonuses["morale"][key] = value

            except Exception:
                pass

    # print(bonuses)
    print(resistances)
    return bonuses, resistances
