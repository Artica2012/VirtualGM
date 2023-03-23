import d20
import discord
from sqlalchemy import Column, Integer, String, JSON, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import Base, get_tracker
from utils.Tracker_Getter import get_tracker_model
from utils.utils import get_guild


class EPF_NPC(Base):
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


async def epf_npc_lookup(
    ctx: discord.ApplicationContext, engine, lookup_engine, bot, name: str, lookup: str, elite: str
):
    async_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(EPF_NPC).where(EPF_NPC.name == lookup))
        data = result.scalars().one()
    await lookup_engine.dispose()

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
        if data.level <= 1:
            hp_mod = -10
        elif data.level <= 4:
            hp_mod = -15
        elif data.level <= 19:
            hp_mod = -20
        else:
            hp_mod = -30
        stat_mod = -2

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)
        initiative_num = 0
        perception = 0
        if guild.initiative is not None:
            try:
                # print(f"Init: {init}")
                perception = int(data.perception_prof) + data.level + stat_mod
                roll = d20.roll(f"{perception}")
                initiative_num = roll.total
                print(initiative_num)
            except Exception:
                initiative_num = 0

        if data.class_dc is None:
            class_dc = 0
        else:
            class_dc = data.class_dc

        async with async_session() as session:
            Tracker = await get_tracker(ctx, engine, id=guild.id)
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
                    ac_base=data.ac_base,
                    class_dc=class_dc,
                    str=data.str,
                    dex=data.dex,
                    con=data.con,
                    itl=data.itl,
                    wis=data.wis,
                    cha=data.cha,
                    fort_prof=data.fort_prof,
                    reflex_prof=data.reflex_prof,
                    will_prof=data.will_prof,
                    perception_prof=data.perception_prof,
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
                )
                session.add(tracker)
            await session.commit()
        await engine.dispose()

        print("Committed")

        Tracker_Model = await get_tracker_model(ctx, bot, engine=engine, guild=guild)
        await Tracker_Model.update_pinned_tracker()
        output_string = f"{data.name} added as {name}"

        await ctx.send_followup(output_string)
        return True
    except Exception:
        await ctx.send_followup("Action Failed, please try again", delete_after=60)
        return False
