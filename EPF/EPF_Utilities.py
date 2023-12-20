import asyncio
import logging

from sqlalchemy import select, false, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import EPF.EPF_Character
from Base.Utilities import Utilities
from EPF.EPF_Character import get_EPF_Character
from database_models import get_tracker, get_condition, get_macro
from error_handling_reporting import error_not_initialized


class EPF_Utilities(Utilities):
    def __init__(self, ctx, guild, engine):
        super().__init__(ctx, guild, engine)

    async def add_character(self, bot, name: str, hp: int, player_bool: bool, init: str, image: str = None, **kwargs):
        await self.ctx.channel.send("Please use `/pf2 import character` or `/pf2 add_npc` to add a character")
        return False

    async def copy_character(self, name: str, new_name: str):
        logging.info("copy_character")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            Condition = await get_condition(self.ctx, self.engine, id=self.guild.id)
            Macro = await get_macro(self.ctx, self.engine, id=self.guild.id)

            # Load up the old character

            split_name = name.split(",")
            async with async_session() as session:
                if len(split_name) > 1:
                    character = await self.retreive_from_vault(name)
                    guild_id = int(split_name[1])
                else:
                    char_result = await session.execute(select(Tracker).where(func.lower(Tracker.name) == name.lower()))
                    character = char_result.scalars().one()
                    guild_id = self.guild.id

                # If initiative is active, roll initiative
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
                    pic=character.pic,
                    active=True,
                    char_class=character.char_class,
                    level=character.level,
                    ac_base=character.ac_base,
                    class_dc=character.class_dc,
                    str=character.str,
                    dex=character.dex,
                    con=character.con,
                    itl=character.itl,
                    wis=character.wis,
                    cha=character.cha,
                    fort_prof=character.fort_prof,
                    will_prof=character.will_prof,
                    reflex_prof=character.reflex_prof,
                    perception_prof=character.perception_prof,
                    class_prof=character.class_prof,
                    key_ability=character.key_ability,
                    unarmored_prof=character.unarmored_prof,
                    light_armor_prof=character.light_armor_prof,
                    medium_armor_prof=character.medium_armor_prof,
                    heavy_armor_prof=character.heavy_armor_prof,
                    unarmed_prof=character.unarmed_prof,
                    simple_prof=character.simple_prof,
                    martial_prof=character.martial_prof,
                    advanced_prof=character.advanced_prof,
                    arcane_prof=character.arcane_prof,
                    divine_prof=character.divine_prof,
                    occult_prof=character.occult_prof,
                    primal_prof=character.primal_prof,
                    acrobatics_prof=character.acrobatics_prof,
                    arcana_prof=character.arcana_prof,
                    athletics_prof=character.athletics_prof,
                    crafting_prof=character.crafting_prof,
                    deception_prof=character.deception_prof,
                    diplomacy_prof=character.diplomacy_prof,
                    intimidation_prof=character.intimidation_prof,
                    medicine_prof=character.medicine_prof,
                    nature_prof=character.nature_prof,
                    occultism_prof=character.occultism_prof,
                    performance_prof=character.performance_prof,
                    religion_prof=character.religion_prof,
                    society_prof=character.society_prof,
                    stealth_prof=character.stealth_prof,
                    survival_prof=character.survival_prof,
                    thievery_prof=character.thievery_prof,
                    lores=character.lores,
                    feats=character.feats,
                    macros=character.macros,
                    attacks=character.attacks,
                    spells=character.spells,
                    bonuses=character.bonuses,
                    eidolon=character.eidolon,
                    partner=character.partner,
                )
                session.add(new_char)
            await session.commit()

            # Load the new character from the database, to get its ID
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(func.lower(Tracker.name) == new_name.lower()))
                new_character = char_result.scalars().one()

            Copy = await get_EPF_Character(new_name, self.ctx, guild=self.guild, engine=self.engine)

            # Copy conditions
            async with async_session() as session:
                Search_Con = await get_condition(self.ctx, self.engine, id=guild_id)
                con_result = await session.execute(
                    select(Search_Con)
                    .where(Search_Con.character_id == character.id)
                    .where(Search_Con.visible == false())
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
                Search_Macro = await get_macro(self.ctx, self.engine, id=guild_id)
                macro_result = await session.execute(
                    select(Search_Macro).where(Search_Macro.character_id == character.id)
                )
                macros = macro_result.scalars().all()

            async with session.begin():
                for mac in macros:
                    await asyncio.sleep(0)
                    new_macro = Macro(character_id=new_character.id, name=mac.name, macro=mac.macro)
                    session.add(new_macro)
                await session.commit()

            await EPF.EPF_Character.calculate(self.ctx, self.engine, new_name, guild=self.guild)

            if self.guild.initiative is not None:
                try:
                    await Copy.roll_initiative()
                except Exception:
                    logging.error("Error Rolling Initiative")

            return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"copy_character: {e}")
            return False

    async def edit_attack(self, character, attack, dmg_stat, attk_stat, crit, dmg, prof):
        # print("editing attack")
        Character_Model = await get_EPF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        try:
            attack_dict = Character_Model.character_model.attacks
            # print(attack_dict)
            if dmg_stat is not None:
                attack_dict[attack]["stat"] = dmg_stat
            if attk_stat is not None:
                attack_dict[attack]["attk_stat"] = attk_stat
            if crit is not None:
                attack_dict[attack]["crit"] = crit
            if dmg is not None:
                attack_dict[attack]["dmg_type"] = dmg
            if prof is not None:
                try:
                    prof = int(prof)
                    attack_dict[attack]["override_prof"] = prof
                except Exception:
                    pass
            # print(attack_dict)
        except Exception as e:
            logging.error(f"EPF utilities edit attack (edit): {e}")
            return False
        try:
            EPF_Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            async with async_session() as session:
                query = await session.execute(select(EPF_Tracker).where(EPF_Tracker.name == character))
                query_char = query.scalars().one()

                query_char.attacks = attack_dict
                await session.commit()
            Character_Model = await get_EPF_Character(character, self.ctx, engine=self.engine, guild=self.guild)
            print(Character_Model.character_model.attacks)
            return True
        except Exception as e:
            logging.error(f"EPF utilities edit attack (write): {e}")
            return False

    async def delete_character(self, character: str):
        Character = await get_EPF_Character(character, self.ctx, engine=self.engine, guild=self.guild)
        if Character.character_model.partner is not None:
            try:
                logging.info("Eidolon/Partner Relationshio")
                Partner = await get_EPF_Character(
                    Character.character_model.partner, self.ctx, engine=self.engine, guild=self.guild
                )
                # IF The character is the Eidolon, delete its entry from its partner
                if Character.character_model.eidolon:
                    logging.info("Eidolon")
                    EPF_Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
                    async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                    async with async_session() as session:
                        char_result = await session.execute(
                            select(EPF_Tracker).where(EPF_Tracker.name == Partner.char_name)
                        )
                        partner_object = char_result.scalars().one()
                        partner_object.partner = None
                        await session.commit()
                else:  # If its not the eidolon, then Character is the user, so delete the eidolon before
                    # deleting the character entry
                    logging.info("Partner")
                    Partner_Util = EPF_Utilities(self.ctx, self.guild, self.engine)
                    await Partner_Util.delete_character(Partner.char_name)
            except Exception as e:
                logging.exception(e)
                return False

        # Now delete the character normally
        return await super().delete_character(character)
