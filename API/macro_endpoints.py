import json

from fastapi import APIRouter
from pydantic import BaseModel

from API.api_utils import get_guild_by_id
from Bot import bot
from database_operations import engine
from utils.Macro_Getter import get_macro_object

router = APIRouter()


class MacroData(BaseModel):
    macro: str
    character: str
    user: int | None = None
    dc: int | None = None
    mod: str | None = ""
    secret: bool | None = False
    guild: int | None = None
    discord_post: bool | None = False


class CreateMacro(BaseModel):
    macro: str
    roll: str
    character: str
    user: int | None = None
    guild: int | None = None


@router.get("/macro/query")
async def get_macros(user: int, character: str, guild: int):
    try:
        print(user, character, guild)
        guild = await get_guild_by_id(guild)
        Macro = await get_macro_object(None, engine, guild)
        macro_list = await Macro.get_macro_list(character.lower())
        return macro_list
    except Exception:
        return []


@router.post("/macro/roll")
async def macro_roll(roll_data: MacroData):
    print(roll_data)
    guild = await get_guild_by_id(roll_data.guild)
    Macro = await get_macro_object(None, engine, guild)

    raw_result = await Macro.raw_roll_macro(roll_data.character, roll_data.macro, roll_data.dc, roll_data.mod)

    if roll_data.discord_post:
        try:
            embed_list = []
            post_output = await Macro.roll_macro(
                roll_data.character, roll_data.macro, roll_data.dc, roll_data.mod, raw=raw_result
            )
            try:
                embed_list.extend(post_output)
            except TypeError:
                embed_list.append(post_output)

            if roll_data.secret:
                await bot.get_channel(int(guild.gm_tracker_channel)).send(embeds=embed_list)
            else:
                await bot.get_channel(int(guild.tracker_channel)).send(embeds=embed_list)
            post = True
        except Exception:
            post = False
    else:
        post = False

    output = {
        "macro": str(roll_data.macro),
        "roll_result": str(raw_result.get("result")),
        "total": int(raw_result.get("result").total),
        "success": raw_result.get("success"),
        "posted": post,
    }
    json_op = json.dumps(output)
    return json_op


@router.post("/macro/create")
async def create_macro(macro_data: CreateMacro):
    guild = await get_guild_by_id(macro_data.guild)
    Macro = await get_macro_object(None, engine, guild)

    response = await Macro.create_macro(macro_data.character, macro_data.macro, macro_data.roll)

    output = {
        "macro": str(macro_data.macro),
        "roll": str(macro_data.roll),
        "character": macro_data.character,
        "response": response,
    }
    json_op = json.dumps(output)
    return json_op
