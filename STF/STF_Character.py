import asyncio
import logging
from math import floor

import d20
import discord
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Character import Character
from STF.STF_Support import STF_Skills
from database_models import get_tracker, get_condition, get_macro
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
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
            result = await session.execute(select(tracker).where(tracker.name == char_name))
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

        super().__init__(char_name, ctx, engine, character, guild)

    async def update(self):
        await calculate(self.ctx, self.engine, self.char_name, guild=self.guild)
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
        self.reflex_mod = self.character_model.reflex_mo

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
        orig_ammount = amount.copy()
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
        return f"1d20+{ParseModifiers(mod)}{ParseModifiers(bonus_mod)}"

    async def weapon_dmg(self, item, crit: bool = False, flat_bonus: str = ""):
        logging.info("weapon_dmg")
        weapon = self.character_model.attacks[item]

        bonus_mod = await skill_mod_calc("dmg", 0, self.bonuses)
        return (
            f"{weapon['dmg_die_num']}d{weapon['dmg_die']}{ParseModifiers(str(weapon['dmg_bonus']))}"
            f"{ParseModifiers(str(bonus_mod))}"
        )

    async def get_weapon(self, item):
        return self.attacks[item]

    async def get_dc(self):
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


async def calculate(ctx, engine, char_name, guild=None):
    logging.info("Updating Character Model")
    guild = await get_guild(ctx, guild=guild)
    # Database boilerplate
    if guild is not None:
        STF_tracker = await get_tracker(ctx, engine, id=guild.id)
    else:
        STF_tracker = await get_tracker(ctx, engine)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    # print(char_name)
    # # TODO Bonuses and Resistances
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
    return bonuses, resistances

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
                # if parsed[0].title() in EPF.EPF_Support.EPF_DMG_Types_Inclusive:
                #     # print(True)
                #     # print("Condition")
                #     # print(f"0: {parsed[0]}, 1: {parsed[1]}, 2: {parsed[2]}")
                #     if parsed[2][-1] == ";":
                #         parsed[2] = parsed[2][:-1]
                #     parsed[0] = parsed[0].lower()
                #     match parsed[1]:
                #         case "r":
                #             resistances["resist"][parsed[0]] = int(parsed[2])
                #         case "w":
                #             resistances["weak"][parsed[0]] = int(parsed[2])
                #         case "i":
                #             resistances["immune"][parsed[0]] = 1
                # item_name = ""
                # specific_weapon = ""
                #
                # print(parsed[0], parsed[0][0])
                # if parsed[0][0] == '"':
                #     print("Opening Quote")
                #     for x, item in enumerate(parsed):
                #         print(x, item)
                #         print(item[-1])
                #         if item[-1] == '"':
                #             item_name = " ".join(parsed[0 : x + 1])
                #             item_name = item_name.strip('"')
                #             parsed = parsed[x + 1 :]
                #             break
                # print(item_name)
                # print(parsed)
                # if item_name != "":
                #     if item_name.title() in await Characte_Model.attack_list():
                #         specific_weapon = f"{item_name},"
                #     else:
                #         parsed = []
                # print(specific_weapon)
                #
                # key = f"{specific_weapon}{parsed[0]}"
                key = parsed[0]
                if parsed[1][1:] == "X":
                    value = int(condition.number)
                else:
                    try:
                        value = int(parsed[1][1:])
                    except ValueError:
                        value = int(parsed[1])

                if parsed[2] == "s" and parsed[1][0] == "+":  # Status Positive
                    if key in bonuses["status_pos"]:
                        if value > bonuses["status_pos"][key]:
                            bonuses["status_pos"][key] = value
                    else:
                        bonuses["status_pos"][key] = value
                elif parsed[2] == "s" and parsed[1][0] == "-":  # Status Negative
                    if key in bonuses["status_neg"]:
                        if value > bonuses["status_neg"][key]:
                            bonuses["status_neg"][key] = value
                    else:
                        bonuses["status_neg"][key] = value
                        # print(f"{key}: {bonuses['status_neg'][key]}")
                elif parsed[2] == "c" and parsed[1][0] == "+":  # Circumstances Positive
                    if key in bonuses["circumstances_pos"]:
                        if value > bonuses["circumstances_pos"][key]:
                            bonuses["circumstances_pos"][key] = value
                    else:
                        bonuses["circumstances_pos"][key] = value
                elif parsed[2] == "c" and parsed[1][0] == "-":  # Circumstances Positive
                    if key in bonuses["circumstances_neg"]:
                        if value > bonuses["circumstances_neg"][key]:
                            bonuses["circumstances_neg"][key] = value
                    else:
                        bonuses["circumstances_neg"][key] = value
                        # print(f"{key}: {bonuses['circumstances_neg'][key]}")
                elif parsed[2] == "i" and parsed[1][0] == "+":  # Item Positive
                    if key in bonuses["item_pos"]:
                        if value > bonuses["item_pos"][key]:
                            bonuses["item_pos"][key] = value
                    else:
                        bonuses["item_pos"][key] = value
                        # print(f"{key}: {bonuses['item_pos'][key]}")
                elif parsed[2] == "i" and parsed[1][0] == "-":  # Item Negative
                    if key in bonuses["item_neg"]:
                        if value > bonuses["item_neg"][key]:
                            bonuses["item_neg"][key] = value
                    else:
                        bonuses["item_neg"][key] = value

            except Exception:
                pass

    # print(bonuses)
    print(resistances)
    return bonuses, resistances
