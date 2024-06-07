import json
from math import ceil

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.security.api_key import APIKey
from pydantic import BaseModel
from cache import AsyncTTL

import Systems.EPF.EPF_Support
from Backend.API.api_utils import get_guild_by_id, update_trackers, post_message, get_username_by_id, get_api_key
from Backend.Database.database_operations import log_roll
from Backend.utils.Automation_Getter import get_automation
from Backend.utils.Fetch_Getter import fetchGetter
from Discord.Bot import bot
from Backend.utils.Char_Getter import get_character
from Backend.utils.Macro_Getter import get_macro_object

router = APIRouter()

system_funcs = {
    None: ["Damage"],
    "PF2": ["Attack", "Save", "Damage"],
    "D4e": ["Attack", "Save", "Damage"],
    "STF": ["Attack", "Save", "Damage"],
    "EPF": ["Auto", "Cast", "Attack", "Save", "Damage"],
}


class AutoRequest(BaseModel):
    character: str
    target: str
    roll: str
    vs: str | None = None
    dc: int | None = None
    guild: int | None = None
    user: int | None = 0
    attk_mod: str | None = ""
    dmg_mod: str | None = ""
    target_mod: str | None = ""
    dmg_type: str | None = ""
    crit: bool | None = False
    healing: bool | None = False
    level: int | None = None
    discord_post: bool | None = True

    def __init__(self, **data):
        super().__init__(**data)
        self.attk_mod = self.target_mod or ""
        self.dmg_mod = self.dmg_mod or ""
        self.target_mod = self.target_mod or ""
        self.dmg_type = self.dmg_type or ""


@AsyncTTL(time_to_live=60, maxsize=64)
@router.get("/auto/system_auto")
async def system_auto(guildid: int, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(guildid)
    try:
        guild_info = {
            "id": guild.id,
            "system": guild.system,
            "gm": guild.gm,
            "members": guild.members,
        }
        output = {"guild_info": guild_info, "functions": system_funcs.get(guild.system)}
        # print(output)
        return json.dumps(output)

    except Exception:
        return []


@AsyncTTL(time_to_live=60, maxsize=64)
@router.get("/auto/dmg_types")
async def dmg_types(guildid: int, api_key: APIKey = Depends(get_api_key)):
    try:
        guild = await get_guild_by_id(guildid)
        if guild.system == "EPF":
            output = Systems.EPF.EPF_Support.EPF_DMG_Types
        else:
            output = []
        return json.dumps(output)

    except Exception:
        return []


@AsyncTTL(time_to_live=60, maxsize=64)
@router.get("/auto/getattacks")
async def get_attacks(user: str, guildid: int, character: str, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(guildid)
    try:
        if guild.system == "EPF":
            Character_Model = await get_character(character, None, guild=guild)
            return await Character_Model.attack_list()
        else:
            Macro = await get_macro_object(None, guild)
            macro_list = await Macro.get_macro_list(character.lower())
            return json.dumps(macro_list)
    except Exception:
        return []


@AsyncTTL(time_to_live=60, maxsize=64)
@router.get("/auto/getspells")
async def get_spells(user: str, guildid: int, character: str, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(guildid)
    try:
        if guild.system == "EPF":
            Character_Model = await get_character(character, None, guild=guild)
            return json.dumps(list(Character_Model.character_model.spells.keys()))
        else:
            return []
    except Exception:
        return []


@AsyncTTL(time_to_live=60, maxsize=64)
@router.get("/auto/getattributes")
async def get_attrib(user: str, guildid: int, character: str, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(guildid)
    try:
        Fetch = await fetchGetter(guild)
        return json.dumps(await Fetch.get_attributes(character))
    except Exception:
        return ["Error"]


@AsyncTTL(time_to_live=60, maxsize=64)
@router.get("/auto/getsaves")
async def get_saves(user: str, guildid: int, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(guildid)
    try:
        Fetch = await fetchGetter(guild)
        return json.dumps(Fetch.get_saves())
    except Exception:
        return ["Error"]


@AsyncTTL(time_to_live=60, maxsize=64)
@router.get("/auto/getspelllevel")
async def get_spelllevel(user: str, guildid: int, character: str, spell: str, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(guildid)

    if guild.system == "EPF":
        try:
            Character_Model = await get_character(character, None, guild=guild)
            spell_name = spell
            spell = Character_Model.get_spell(spell_name)
            # print(spell_name)
            # print(spell)
        except Exception:
            return []

        try:
            try:
                if spell["tradition"] == "NPC":
                    return [spell["cast_level"]]
            except KeyError:
                pass

            try:
                min_level = spell["level"]
            except KeyError:
                min_level = spell["lvl"]

            # print(min_level)

            # Cantrips are always at max spell rank
            if min_level == 0:
                return [ceil(Character_Model.character_model.level / 2)]
            max_level = ceil(Character_Model.character_model.level / 2)

            if "complex" in spell:
                if "interval" in spell["heighten"]:
                    interval_level = spell["heighten"]["interval"]
                elif "set" in spell["heighten"]:
                    level_list = [min_level]
                    for key in spell["heighten"]["set"].keys():
                        level_list.append(int(key))
                    level_list.sort()
                    return level_list
                else:
                    interval_level = 1
            else:
                if spell["heightening"]["type"] == "interval":
                    interval_level = spell["heightening"]["interval"]
                elif spell["heightening"]["type"] == "fixed":
                    level_list = [min_level]
                    for key in spell["heightening"]["type"]["interval"]:
                        level_list.append(key)
                    return level_list
                else:
                    interval_level = 1

            level_list = []
            for num in range(min_level, max_level + 1, interval_level):
                level_list.append(num)
            return json.dumps(level_list)
        except Exception:
            return []


@router.post("/auto/attack")
async def api_attack(body: AutoRequest, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Automation = await get_automation(None, guild=guild)
    # print(body)
    try:
        auto_data = await Automation.attack(
            body.character, body.target, body.roll, body.vs, body.attk_mod, body.target_mod
        )
        background_tasks.add_task(update_trackers, guild)
    except Exception as e:
        # print(e)
        return {"success": "failure", "output": e}

    if body.discord_post:
        embed = auto_data.embed
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")
        background_tasks.add_task(post_message, guild, embed=embed)

    log_output = f"{auto_data.raw['roll']}:\n{auto_data.raw['string']}"
    await log_roll(guild.id, body.character, log_output)

    return json.dumps(auto_data.raw)


@router.post("/auto/save")
async def api_save(body: AutoRequest, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Automation = await get_automation(None, guild=guild)
    try:
        auto_data = await Automation.save(body.character, body.target, body.roll, body.vs, body.attk_mod)
    except Exception as e:
        # print(e)
        return {"success": "failure", "output": e}

    if body.discord_post:
        embed = auto_data.embed
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")
        background_tasks.add_task(post_message, guild, embed=embed)

    log_output = f"{auto_data.raw['roll']}:\n{auto_data.raw['string']}"
    await log_roll(guild.id, body.character, log_output)

    return json.dumps(auto_data.raw)


@router.post("/auto/damage")
async def api_damage(body: AutoRequest, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Automation = await get_automation(None, guild=guild)
    # print(body)
    try:
        auto_data = await Automation.damage(
            bot, body.character, body.target, body.roll, body.dmg_mod, body.healing, body.dmg_type, crit=body.crit
        )
    except Exception as e:
        # print(e)
        return {"success": "failure", "output": e}

    if body.discord_post:
        embed = auto_data.embed
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")
        background_tasks.add_task(post_message, guild, embed=embed)

    log_output = f"{auto_data.raw['roll']}:\n{auto_data.raw['string']}"
    await log_roll(guild.id, body.character, log_output)

    return json.dumps(auto_data.raw)


@router.post("/auto/auto")
async def api_auto(body: AutoRequest, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Automation = await get_automation(None, guild=guild)
    try:
        auto_data = await Automation.auto(
            bot, body.character, body.target, body.roll, body.attk_mod, body.target_mod, body.dmg_mod, body.dmg_type
        )
    except Exception as e:
        # print(e)
        return {"success": "failure", "output": e}

    if body.discord_post:
        embed = auto_data.embed
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")
        background_tasks.add_task(post_message, guild, embed=embed)

    log_output = f"{auto_data.raw['roll']}:\n{auto_data.raw['string']}"
    await log_roll(guild.id, body.character, log_output)

    return json.dumps(auto_data.raw)


@router.post("/auto/cast")
async def api_cast(body: AutoRequest, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Automation = await get_automation(None, guild=guild)
    try:
        auto_data = await Automation.cast(
            bot,
            body.character,
            body.target,
            body.roll,
            body.level,
            body.attk_mod,
            body.target_mod,
            body.dmg_mod,
            body.dmg_type,
        )
    except Exception as e:
        # print(e)
        return {"success": "failure", "output": e}

    if body.discord_post:
        embed = auto_data.embed
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")
        background_tasks.add_task(post_message, guild, embed=embed)

    log_output = f"{auto_data.raw['roll']}:\n{auto_data.raw['string']}"
    await log_roll(guild.id, body.character, log_output)

    return json.dumps(auto_data.raw)
