import logging

import discord
from sqlalchemy import Column, Integer, String, JSON, select, func

import Systems.EPF.EPF_Character
from Backend.Database.engine import async_session, lookup_session
from Systems.EPF.EPF_Automation_Data import EPF_retreive_complex_data
from Systems.EPF.EPF_Character import get_EPF_Character, delete_intested_items
from Backend.Database.database_models import get_tracker, LookupBase
from Backend.utils.parsing import ParseModifiers
from Backend.utils.utils import get_guild


class EPF_NPC(LookupBase):
    __tablename__ = "EPF_npcs"

    # The original tracker table
    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(), nullable=False, unique=True)
    max_hp = Column(Integer(), default=1)

    # General
    type = Column(String(), nullable=False)
    level = Column(Integer(), nullable=False)
    ac_base = Column(Integer(), nullable=False)
    class_dc = Column(Integer(), nullable=False)

    # Stats
    str = Column(Integer(), nullable=False)
    dex = Column(Integer(), nullable=False)
    con = Column(Integer(), nullable=False)
    itl = Column(Integer(), nullable=False)
    wis = Column(Integer(), nullable=False)
    cha = Column(Integer(), nullable=False)

    # Saves
    fort_prof = Column(Integer(), nullable=False)
    will_prof = Column(Integer(), nullable=False)
    reflex_prof = Column(Integer(), nullable=False)

    # Proficiencies
    perception_prof = Column(Integer(), nullable=False)

    arcane_prof = Column(Integer(), nullable=False)
    divine_prof = Column(Integer(), nullable=False)
    occult_prof = Column(Integer(), nullable=False)
    primal_prof = Column(Integer(), nullable=False)

    acrobatics_prof = Column(Integer(), nullable=False)
    arcana_prof = Column(Integer(), nullable=False)
    athletics_prof = Column(Integer(), nullable=False)
    crafting_prof = Column(Integer(), nullable=False)
    deception_prof = Column(Integer(), nullable=False)
    diplomacy_prof = Column(Integer(), nullable=False)
    intimidation_prof = Column(Integer(), nullable=False)
    medicine_prof = Column(Integer(), nullable=False)
    nature_prof = Column(Integer(), nullable=False)
    occultism_prof = Column(Integer(), nullable=False)
    performance_prof = Column(Integer(), nullable=False)
    religion_prof = Column(Integer(), nullable=False)
    society_prof = Column(Integer(), nullable=False)
    stealth_prof = Column(Integer(), nullable=False)
    survival_prof = Column(Integer(), nullable=False)
    thievery_prof = Column(Integer(), nullable=False)

    # Plan to save parsable lists here

    # Calculated stats
    resistance = Column(JSON())
    attacks = Column(JSON())
    spells = Column(JSON())


async def epf_npc_lookup(ctx: discord.ApplicationContext, name: str, lookup: str, elite: str, image: str = None):
    # Check to make sure name is not in use

    Tracker = await get_tracker(ctx)
    async with async_session() as session:
        result = await session.execute(select(Tracker).where(func.lower(Tracker.name) == name.lower()))
        character = result.scalars().all()
    if len(character) > 0:
        raise NameError

    async with lookup_session() as session:
        result = await session.execute(select(EPF_NPC).where(EPF_NPC.name == lookup))
        data = result.scalars().one()

    # print(data.resistance)

    # elite/weak adjustments
    hp_mod = 0
    stat_mod = 0
    if elite == "elite":
        if data.level <= 1:
            hp_mod = 10
        elif data.level <= 4:
            hp_mod = 15
        elif data.level <= 19:
            hp_mod = 20
        else:
            hp_mod = 30
        stat_mod = 2
    if elite == "weak":
        if data.level < 1:
            pass
        elif data.level <= 2:
            hp_mod = -10
        elif data.level <= 5:
            hp_mod = -15
        elif data.level <= 20:
            hp_mod = -20
        else:
            hp_mod = -30
        stat_mod = -2

    spell_book = {}
    for spell in data.spells.keys():
        spell_data = await EPF_retreive_complex_data(spell)
        if len(spell_data) > 0:
            for s in spell_data:
                complex_spell = s.data
                complex_spell["ability"] = data.spells[spell]["ability"]
                complex_spell["trad"] = "NPC"
                complex_spell["dc"] = data.spells[spell]["dc"]
                complex_spell["proficiency"] = data.spells[spell]["proficiency"]
                spell_book[s.display_name] = complex_spell
        else:
            spell_book[spell] = data.spells[spell]

    try:
        guild = await get_guild(ctx, None)
        initiative_num = 0
        perception = 0

        if data.class_dc is None:
            class_dc = 0
        else:
            class_dc = data.class_dc

        async with async_session() as session:
            async with session.begin():
                tracker = Tracker(
                    name=name,
                    init=initiative_num,
                    player=False,
                    user=ctx.user.id,
                    current_hp=data.max_hp + hp_mod,
                    max_hp=data.max_hp + hp_mod,
                    temp_hp=0,
                    init_string=f"{perception}",
                    active=True,
                    char_class=data.type,
                    level=data.level,
                    ac_base=data.ac_base + stat_mod,
                    class_dc=class_dc,
                    str=data.str,
                    dex=data.dex,
                    con=data.con,
                    itl=data.itl,
                    wis=data.wis,
                    cha=data.cha,
                    fort_prof=data.fort_prof + stat_mod,
                    reflex_prof=data.reflex_prof + stat_mod,
                    will_prof=data.will_prof + stat_mod,
                    perception_prof=data.perception_prof + stat_mod,
                    class_prof=0,
                    key_ability="",
                    unarmored_prof=0,
                    light_armor_prof=0,
                    medium_armor_prof=0,
                    heavy_armor_prof=0,
                    unarmed_prof=0,
                    simple_prof=0,
                    martial_prof=0,
                    advanced_prof=0,
                    arcane_prof=data.arcane_prof,
                    divine_prof=data.divine_prof,
                    occult_prof=data.occult_prof,
                    primal_prof=data.primal_prof,
                    acrobatics_prof=data.acrobatics_prof,
                    arcana_prof=data.arcana_prof,
                    athletics_prof=data.athletics_prof,
                    crafting_prof=data.crafting_prof,
                    deception_prof=data.deception_prof,
                    diplomacy_prof=data.diplomacy_prof,
                    intimidation_prof=data.intimidation_prof,
                    medicine_prof=data.medicine_prof,
                    nature_prof=data.nature_prof,
                    occultism_prof=data.occultism_prof,
                    performance_prof=data.performance_prof,
                    religion_prof=data.religion_prof,
                    society_prof=data.society_prof,
                    stealth_prof=data.stealth_prof,
                    survival_prof=data.survival_prof,
                    thievery_prof=data.thievery_prof,
                    lores="",
                    feats="",
                    resistance=data.resistance,
                    macros="",
                    attacks=data.attacks,
                    spells=data.spells,
                    pic=image,
                )
                session.add(tracker)
            await session.commit()

        # print("Committed")
        # print(f"Stat_Mod: {stat_mod}")
        Charater_Model = await get_EPF_Character(name, ctx, guild=guild)
        if stat_mod != 0:
            # print("Write the elite/weak modifiers")
            stat_mod = ParseModifiers(f"{stat_mod}")
            await Charater_Model.update()

            ewdata = (
                f"attack {stat_mod} i, dmg {stat_mod} i, fort {stat_mod} i, reflex {stat_mod} i, will {stat_mod} i,"
                f" acrobatics {stat_mod} i,  arcana {stat_mod} i, athletics {stat_mod} i,"
                f" crafting {stat_mod} i, deception {stat_mod} i, diplomacy {stat_mod} i, intimidation"
                f" {stat_mod} i, medicine {stat_mod} i, nature {stat_mod} i, occultism {stat_mod} i,"
                f"  performance {stat_mod} i, religion {stat_mod} i, society {stat_mod} i, stealth"
                f" {stat_mod} i, survival {stat_mod} i, thievery {stat_mod} i"
            )
            # Only effect perception for elite
            if stat_mod > 0:
                ewdata += f", perception {stat_mod} i,"

            result = await Charater_Model.set_cc(
                elite,
                True,
                0,
                "Round",
                False,
                data=ewdata,
                visible=False,
                update=False,
            )
        # print(data.type)
        if "hazard" in data.type.lower():
            await Charater_Model.set_cc(
                "Hazard", True, 0, "Round", False, data="init-skill stealth", visible=False, update=False
            )
        # print(data.resistance)
        await write_resitances(data.resistance, Charater_Model, ctx, guild, overwrite=False)

        await Charater_Model.update()
        # Tracker_Model = await get_tracker_model(ctx, bot, engine=engine, guild=guild)
        # await Tracker_Model.update_pinned_tracker()
        # output_string = f"{data.name} added as {name}"

        # await ctx.send_followup(output_string)
        if guild.initiative is not None:
            try:
                await Charater_Model.roll_initiative()
            except Exception:
                logging.error("Error Rolling initiative")

        return True
    except Exception:
        await ctx.send_followup("Action Failed, please try again", delete_after=60)
        return False


async def write_resitances(
    resistance: dict, Character_Model: Systems.EPF.EPF_Character.EPF_Character, ctx, guild, overwrite=True
):
    # print("write resistances")
    # First delete out all the old resistances
    if overwrite:
        await delete_intested_items(Character_Model.char_name, ctx, guild)

    # Then write the new ones
    # print(resistance)
    try:
        for key, value in resistance["resist"].items():
            # print(key)
            # print(type(value))
            if type(value) == dict:
                exceptions = ""
                for item in value["exceptions"]:
                    # print(item)
                    exceptions = exceptions + " " + item
                condition_string = f"{key} r {value['value']} e {exceptions}"
                value = value["value"]
            else:
                condition_string = f"{key} r {value}"
            # print(condition_string)

            await Character_Model.set_cc(
                key, True, value, "Round", False, data=condition_string, visible=False, update=False
            )
        for key, value in resistance["weak"].items():
            # print(key)
            if type(value) == dict:
                exceptions = ""
                for item in value["exceptions"]:
                    exceptions = exceptions + " " + item
                condition_string = f"{key} w {value['value']} e {exceptions}"
                value = value["value"]
            else:
                condition_string = f"{key} w {value}"
            # print(condition_string)

            await Character_Model.set_cc(
                key, True, value, "Round", False, data=condition_string, visible=False, update=False
            )
        for key in resistance["immune"].keys():
            # print(key)
            if type(value) == dict:
                exceptions = ""
                for item in value["exceptions"]:
                    exceptions = exceptions + " " + item
                condition_string = f"{key} i {exceptions}"
            else:
                condition_string = f"{key} i"
            # print(condition_string)

            await Character_Model.set_cc(
                key, True, 1, "Round", False, data=condition_string, visible=False, update=False
            )
        if "other" in resistance:
            # print("other")
            if "init-skill" in resistance["other"]:
                # print("init-skill")
                await Character_Model.set_cc(
                    "init-skill",
                    True,
                    1,
                    "Round",
                    False,
                    data=f"init-skill {resistance['other']['init-skill']}",
                    visible=False,
                    update=False,
                )
            if "hardness" in resistance["other"]:
                await Character_Model.set_cc(
                    "hardness",
                    True,
                    1,
                    "Round",
                    False,
                    data=f"hardness {resistance['other']['hardness']}",
                    visible=True,
                    update=False,
                )

        return True
    except Exception:
        return False
