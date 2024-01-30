import json

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.openapi.models import APIKey
from pydantic import BaseModel

from API.api_utils import get_guild_by_id, post_message, get_api_key, get_username_by_id
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
    discord_post: bool | None = True


class CreateMacro(BaseModel):
    macro: str
    roll: str
    character: str
    user: int | None = None
    guild: int | None = None


@router.get("/macro/query")
async def get_macros(user: int, character: str, guildid: int, api_key: APIKey = Depends(get_api_key)):
    try:
        # print(user, character, guildid)
        guild = await get_guild_by_id(guildid)
        Macro = await get_macro_object(None, engine, guild)
        macro_list = await Macro.get_macro_list(character.lower())
        return json.dumps(macro_list)
    except Exception:
        return []


@router.post("/macro/roll")
async def macro_roll(roll_data: MacroData, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    # print(roll_data)
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
                user_name = get_username_by_id(roll_data.user)
                for post in post_output:
                    post.set_footer(text=f"via Web by {user_name}")
                embed_list.extend(post_output)
            except TypeError:
                post_output.set_footer(text=f"via Web by {get_username_by_id(roll_data.user)}")
                embed_list.append(post_output)

            if roll_data.secret:
                background_tasks.add_task(post_message, guild, embeds=embed_list, gm=True)
            else:
                background_tasks.add_task(post_message, guild, embeds=embed_list)
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
async def create_macro(macro_data: CreateMacro, api_key: APIKey = Depends(get_api_key)):
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
