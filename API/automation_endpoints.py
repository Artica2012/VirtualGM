from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from API.api_utils import get_guild_by_id, update_trackers, post_message, get_username_by_id
from database_operations import engine
from utils.Automation_Getter import get_automation

router = APIRouter()


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


@router.post("/auto/attack")
async def api_attack(body: AutoRequest, background_tasks: BackgroundTasks):
    guild = await get_guild_by_id(body.guild)
    Automation = await get_automation(None, guild=guild, engine=engine)

    auto_data = await Automation.attack(body.character, body.target, body.roll, body.vs, body.attk_mod, body.target_mod)
    background_tasks.add_task(update_trackers, guild)

    if body.discord_post:
        embed = auto_data.embed
        embed.set_footer(text=f"via Web by {get_username_by_id(body.user)}")
        background_tasks.add_task(post_message, guild, embed=embed)

    return auto_data.raw
