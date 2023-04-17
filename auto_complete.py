# auto_complete.py

# Consolidating all of the autocompletes into one place.

import datetime

# imports
import logging

import discord
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database_models import get_tracker, Character_Vault
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA
from database_operations import get_asyncio_db_engine
from utils.Auto_Complete_Getter import get_autocomplete
from utils.utils import get_guild


async def hard_lock(ctx: discord.ApplicationContext, name: str):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    Tracker = await get_tracker(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker.user).where(Tracker.name == name))
            user = result.scalars().one()
            # print(user)
            # print(ctx.user.id)

        if await gm_check(ctx, engine) or ctx.interaction.user.id == user:
            return True
        else:
            return False
    except Exception:
        logging.error("hard_lock")
        return False


async def gm_check(ctx, engine):
    # bughunt code
    logging.info(f"{datetime.datetime.now()} - attack_cog gm_check")
    try:
        guild = await get_guild(ctx, None)
        if int(guild.gm) != int(ctx.interaction.user.id):
            return False
        else:
            return True
    except Exception:
        return False


# Autocompletes
# returns a list of all characters
async def character_select(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.character_select()


# Returns a list of all characters owned by the player, or all characters if the player is the GM
async def character_select_gm(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.character_select(gm=True)


async def character_select_player(ctx: discord.AutocompleteContext):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    try:
        guild = await get_guild(ctx, None)
        AutoComplete = await get_autocomplete(ctx, guild=guild)
        return await AutoComplete.character_select(gm=True)
    except NoResultFound:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            logging.info("Searching Character Vault")
            print(ctx.interaction.user.id)
            print(ctx.interaction.guild.id)
            result = await session.execute(
                select(Character_Vault)
                .where(Character_Vault.user == ctx.interaction.user.id)
                .where(Character_Vault.disc_guild_id == ctx.interaction.guild.id)
                # .order_by(Character_Vault.name.desc()) # This is causing duplicates - BUG
            )
            charcter_list = result.scalars().all()
            if ctx.value != "":
                val = ctx.value.lower()
                return [f"{char.name}, {char.guild_id}" for char in charcter_list if val in char.name.lower()]
            else:
                return [f"{char.name}, {char.guild_id}" for char in charcter_list]


async def character_select_con(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    char_list: list = await AutoComplete.character_select()
    # print(char_list)
    char_list.extend(["All PCs", "All NPCs"])
    # print(char_list)
    return char_list


async def a_save_target_custom(ctx: discord.AutocompleteContext):
    guild = await get_guild(ctx, None)
    AutoComplete = await get_autocomplete(ctx, guild=guild)
    if guild.system == "D4e":
        return await AutoComplete.cc_select(flex=True)
    else:
        return await AutoComplete.character_select()


async def npc_select(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.npc_select()


async def add_condition_select(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.add_condition_select()


async def macro_select(ctx: discord.AutocompleteContext):
    try:
        guild = await get_guild(ctx, None)
        AutoComplete = await get_autocomplete(ctx, guild=guild)
        return await AutoComplete.macro_select()
    except NoResultFound:
        character = ctx.options["character"]
        char_split = character.split(",")
        if len(char_split) > 1:
            guild_id = int(char_split[1].strip())
            AutoComplete = await get_autocomplete(ctx, id=guild_id)
            return await AutoComplete.macro_select()


async def a_macro_select(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.macro_select(attk=True)


async def a_d_macro_select(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.macro_select(attk=True, dmg=True)


async def cc_select(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.cc_select()


async def cc_select_no_time(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.cc_select(no_time=True)


async def save_select(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.save_select()


async def get_attributes(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.get_attributes()


async def attacks(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.attacks()


async def stats(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.stats()


async def dmg_type(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.dmg_types()


async def var_dmg_type(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.dmg_types(var=True)


async def npc_search(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.npc_search()


async def spell_list(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.spell_list()


async def spell_level(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.spell_level()


async def initiative(ctx: discord.AutocompleteContext):
    AutoComplete = await get_autocomplete(ctx)
    return await AutoComplete.init()
