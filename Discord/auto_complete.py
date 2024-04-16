# auto_complete.py

# Consolidating all the autocompletes into one place.

import datetime
import logging

import discord
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound

from Backend.Database.database_models import get_tracker, Character_Vault
from Backend.Database.engine import async_session
from Backend.utils.Auto_Complete_Getter import get_autocomplete
from Backend.utils.utils import get_guild


async def hard_lock(ctx: discord.ApplicationContext, name: str):
    try:
        Tracker = await get_tracker(ctx)

        async with async_session() as session:
            result = await session.execute(select(Tracker.user).where(func.lower(Tracker.name) == name.lower()))
            user = result.scalars().one()

        if await gm_check(ctx) or ctx.interaction.user.id == user:
            return True
        else:
            return False
    except Exception:
        logging.error("hard_lock")
        return False


async def gm_check(ctx):
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
    try:
        # print("Char Select No GM")
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.character_select()
    except Exception:
        return []


async def character_select_multi(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.character_select(multi=True)
    except Exception:
        return []


async def red_no_net_character_select_multi(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.character_select(multi=True, net=False)
    except Exception:
        return []


async def red_net_character_select_multi(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.character_select(multi=True, net=True)
    except Exception:
        return []


async def red_net_character_select_gm(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.character_select(gm=True, net=True)
    except Exception:
        return []


# Returns a list of all characters owned by the player, or all characters if the player is the GM
async def character_select_gm(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.character_select(gm=True)
    except Exception:
        return []


async def character_vault_search(ctx: discord.AutocompleteContext):
    # print("triggered")
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.vault_search(gm=True)
    except Exception:
        return []


async def character_select_player(ctx: discord.AutocompleteContext):
    try:
        try:
            guild = await get_guild(ctx, None)
            AutoComplete = await get_autocomplete(ctx, guild=guild)
            return await AutoComplete.character_select(gm=True, all=True)
        except NoResultFound:
            async with async_session() as session:
                logging.info("Searching Character Vault")
                result = await session.execute(
                    select(Character_Vault)
                    .where(Character_Vault.user == ctx.interaction.user.id)
                    .where(Character_Vault.disc_guild_id == ctx.interaction.guild.id)
                )
                charcter_list = result.scalars().all()
                if ctx.value != "":
                    val = ctx.value.lower()
                    return [f"{char.name}, {char.guild_id}" for char in charcter_list if val in char.name.lower()]
                else:
                    return [f"{char.name}, {char.guild_id}" for char in charcter_list]
    except Exception:
        return []


async def character_select_con(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        char_list: list = await AutoComplete.character_select()
        char_list.extend(["All PCs", "All NPCs"])
        return char_list
    except Exception:
        return []


async def a_save_target_custom(ctx: discord.AutocompleteContext):
    try:
        guild = await get_guild(ctx, None)
        AutoComplete = await get_autocomplete(ctx, guild=guild)
        if guild.system == "D4e":
            return await AutoComplete.cc_select(flex=True)
        else:
            return await AutoComplete.character_select()
    except Exception:
        return []


async def a_save_target_custom_multi(ctx: discord.AutocompleteContext):
    try:
        guild = await get_guild(ctx, None)
        AutoComplete = await get_autocomplete(ctx, guild=guild)
        if guild.system == "D4e":
            return await AutoComplete.cc_select(flex=True)
        else:
            return await AutoComplete.character_select(multi=True)
    except Exception:
        return []


async def npc_select(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.npc_select()
    except Exception:
        return []


async def add_condition_select(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.add_condition_select()
    except Exception:
        return []


async def macro_select(ctx: discord.AutocompleteContext):
    try:
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
    except Exception:
        return []


async def a_macro_select(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.macro_select(attk=True)
    except Exception:
        return []


async def auto_macro_select(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.macro_select(attk=True, auto=True)
    except Exception:
        return []


async def net_macro_select(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.macro_select(attk=False, auto=False, net=True)
    except Exception:
        return []


async def a_d_macro_select(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.macro_select(attk=True, dmg=True)
    except Exception:
        return []


async def cc_select(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.cc_select()
    except Exception:
        return []


async def cc_select_no_time(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.cc_select(no_time=True)
    except Exception:
        return []


async def save_select(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.save_select()
    except Exception:
        return []


async def get_attributes(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.get_attributes()
    except Exception:
        return []


async def attacks(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.attacks()
    except Exception:
        return []


async def stats(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.stats()
    except Exception:
        return []


async def dmg_type(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.dmg_types()
    except Exception:
        return []


async def var_dmg_type(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.dmg_types(var=True)
    except Exception:
        return []


async def npc_search(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.npc_search()
    except Exception:
        return []


async def spell_list(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.spell_list()
    except Exception:
        return []


async def spell_level(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.spell_level()
    except Exception:
        return []


async def initiative(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.init()
    except Exception:
        return []


async def flex_ac(ctx: discord.AutocompleteContext):
    try:
        AutoComplete = await get_autocomplete(ctx)
        return await AutoComplete.flex()
    except Exception:
        return []
