import json
import logging

import d20
import discord
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.openapi.models import APIKey
from pydantic import BaseModel
from sqlalchemy import select, true
from cache import AsyncTTL

from Backend.API.api_utils import (
    get_guild_by_id,
    gm_check,
    update_trackers,
    post_message,
    get_username_by_id,
    get_api_key,
)
from Backend.Database.engine import async_session
from Discord.Bot import bot
from Backend.Database.database_models import get_condition, Global
from Backend.utils.Char_Getter import get_character
from Backend.utils.Tracker_Getter import get_tracker_model


router = APIRouter()


class InitManage(BaseModel):
    user: int | None = 0
    guild: int | None = None


class InitSet(BaseModel):
    character: str
    roll: str
    guild: int | None = None
    user: int | None = 0


class HPSet(BaseModel):
    character: str
    roll: str
    heal: bool | None = False
    thp: bool | None = False
    guild: int | None = None
    user: int | None = 0


class ConditionBody(BaseModel):
    character: str
    title: str
    counter: bool | None = False  # True for counter, False for condition
    number: int | None = None
    unit: str | None = "Round"
    auto: bool | None = False
    flex: bool | None = False
    data: str | None = ""
    linked_character: str | None = None
    guild: int | None = None
    user: int | None = 0
    discord_post: bool | None = True


@router.get("/init/tracker")
async def get_tracker(user: str, guildid: int, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(guildid)
    Tracker_Model = await get_tracker_model(None, guild=guild)
    output_model = await Tracker_Model.raw_tracker_output(guild.initiative)
    guild_info = {
        "id": guild.id,
        "system": guild.system,
        "gm": guild.gm,
        "members": guild.members,
    }

    # print(output_model)
    output = {"guild": guildid, "output": output_model, "init_pos": guild.initiative, "guild_info": guild_info}
    op = json.dumps(output)
    # print(op)
    return op


@AsyncTTL(time_to_live=60, maxsize=64)
@router.get("/init/user_tables")
async def get_user_tables(user: str, api_key: APIKey = Depends(get_api_key)):
    output = {}
    async with async_session() as session:
        result = await session.execute(select(Global))
        all_guilds = result.scalars().all()
    # print(len(all_guilds))
    # print(all_guilds)

    for guild in all_guilds:
        try:
            if int(user) in guild.members:
                guild_info = {
                    "system": guild.system,
                    "gm": guild.gm,
                    "members": guild.members,
                }

                g = {
                    "id": guild.id,
                    "server": bot.get_guild(guild.guild_id).name,
                    "channel": bot.get_channel(guild.tracker_channel).name,
                    "guild_info": guild_info,
                }

                output[guild.id] = g

        except TypeError:
            pass
        except AttributeError:
            pass

    return json.dumps(output)


@router.post("/init/next")
async def init_start(request: InitManage, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(request.guild)
    Tracker_Model = await get_tracker_model(None, guild=guild)
    try:
        # await Tracker_Model.advance_initiative()
        success = await Tracker_Model.block_next(None, request.user)

    except Exception as e:
        logging.warning(f"api /init/next: {e}")
        success = False

    if success:
        background_tasks.add_task(Tracker_Model.block_post_init)

    return json.dumps({"success": success})


@router.post("/init/end")
async def init_end(request: InitManage, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(request.guild)
    GM = gm_check(str(request.user), guild)
    if GM:
        try:
            Tracker_Model = await get_tracker_model(None, guild=guild)
            await Tracker_Model.end()
            success = True
        except Exception as e:
            logging.warning(f"api /init/next: {e}")
            success = False
    else:
        success = False

    if success:
        background_tasks.add_task(post_message, guild, message="Initiative Ended")

    return {"success": success}


@router.post("/init/set")
async def init_set(request: InitSet, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(request.guild)
    Character_Model = await get_character(request.character, None, guild=guild)
    success_string = await Character_Model.set_init(request.roll)

    background_tasks.add_task(update_trackers, guild)

    return json.dumps(
        {"success": success_string, "character": request.character, "roll": request.roll, "user": request.user}
    )


@router.post("/init/hp")
async def hp_set(body: HPSet, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Character_Model = await get_character(body.character, None, guild=guild)
    try:
        rolled_value = int(d20.roll(body.roll).total)
    except Exception:
        return {"success": False}

    if body.thp:
        await Character_Model.add_thp(rolled_value)
        success = True
        output_string = f"{rolled_value} temporary hit points added to {Character_Model.char_name}"
        color = discord.Color.dark_gold()
    else:
        success = await Character_Model.change_hp(rolled_value, body.heal, post=False)
        if body.heal:
            color = discord.Color.dark_green()
        else:
            color = discord.Color.dark_red()
        output_string = f"{Character_Model.char_name} {'healed' if body.heal else 'damaged'} for {rolled_value}. "
        if Character_Model.player:
            output_string += f"\n New HP: {Character_Model.current_hp}/{Character_Model.max_hp}"
        else:
            output_string += f"\n {await Character_Model.calculate_hp()}"

    # api raw output
    output = {
        "success": success,
        "roll": body.roll,
        "hp": Character_Model.current_hp,
        "value": rolled_value,
        "character": body.character,
    }
    # Discord posting nonsense
    embed = discord.Embed(
        title=f"{Character_Model.char_name}",
        fields=[
            discord.EmbedField(
                name="HP: ",
                value=output_string,
                inline=False,
            ),
        ],
        color=color,
    )
    embed.set_thumbnail(url=Character_Model.pic)
    embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")
    background_tasks.add_task(post_message, guild, embed=embed)

    return json.dumps(output)


@router.get("/cc/query")
async def get_cc_query(
    user: int, character: str, guildid: int, list: bool = True, api_key: APIKey = Depends(get_api_key)
):
    guild = await get_guild_by_id(guildid)
    Character_Model = await get_character(character, None, guild=guild)
    if list:
        Condition = await get_condition(None, id=guild.id)
        async with async_session() as session:
            result = await session.execute(
                select(Condition.title)
                .where(Condition.character_id == Character_Model.id)
                .where(Condition.visible == true())
                .order_by(Condition.title.asc())
            )
            return result.scalars().all()
    else:
        return json.dumps(await Character_Model.conditions())


@router.post("/cc/new")
async def api_add_cc(body: ConditionBody, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Character_Model = await get_character(body.character, None, guild=guild)

    success = await Character_Model.set_cc(
        body.title,
        body.counter,
        body.number,
        body.unit,
        body.auto,
        flex=body.flex,
        data=body.data,
        target=body.linked_character,
    )

    output = {"success": success}
    # print(output)

    # discord posting nonsense
    if body.discord_post:
        embed = discord.Embed(
            title=Character_Model.char_name.title(),
            fields=[
                discord.EmbedField(
                    name="Success", value=f"{body.title} {body.number if body.number != None else ''} added."
                )
            ],
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=Character_Model.pic)
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")
        if success:
            background_tasks.add_task(post_message, guild, embed=embed)
            background_tasks.add_task(update_trackers, guild)

    return output


@router.delete("/cc/delete")
async def delete_cc(body: ConditionBody, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Character_Model = await get_character(body.character, None, guild=guild)
    result = await Character_Model.delete_cc(body.title)
    if result and body.discord_post:
        embed = discord.Embed(
            title=Character_Model.char_name.title(),
            fields=[
                discord.EmbedField(
                    name=body.title.title(), value=f"{body.title} deleted from {Character_Model.char_name}."
                )
            ],
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=Character_Model.pic)
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")

        background_tasks.add_task(post_message, guild, embed=embed)
        background_tasks.add_task(update_trackers, guild)

    return {"success": result, "title": body.title}


@router.post("/cc/modify")
async def modify_cc(body: ConditionBody, background_tasks: BackgroundTasks, api_key: APIKey = Depends(get_api_key)):
    guild = await get_guild_by_id(body.guild)
    Character_Model = await get_character(body.character, None, guild=guild)
    success = False
    if body.number is not None:
        success = await Character_Model.edit_cc(body.title, body.number)

    if success and body.discord_post:
        embed = discord.Embed(
            title=Character_Model.char_name.title(),
            fields=[
                discord.EmbedField(
                    name=body.title.title(), value=f"{body.title} on {Character_Model.char_name} set to {body.number}."
                )
            ],
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=Character_Model.pic)
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")

        background_tasks.add_task(post_message, guild, embed=embed)
        background_tasks.add_task(update_trackers, guild)

    return {"success": success, "title": body.title}
