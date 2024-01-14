import logging

import d20
from fastapi import APIRouter
from pydantic import BaseModel

from API.api_utils import get_guild_by_id, get_username_by_id
from Bot import bot
from error_handling_reporting import API_ErrorReport
from utils.parsing import opposed_roll, eval_success
from utils.utils import relabel_roll
import json

router = APIRouter()


class RollData(BaseModel):
    roll: str
    user: int | None = None
    dc: int | None = None
    secret: bool | None = False
    guild: int | None = None
    discord_post: bool | None = False


@router.post("/roll")
async def api_roll(roll_data: RollData):
    print(roll_data)
    roll = relabel_roll(roll_data.roll)
    try:
        roll_result = d20.roll(roll)
        roll_str = opposed_roll(roll_result, d20.roll(f"{roll_data.dc}")) if roll_data.dc else roll_result
        if roll_data.dc is not None:
            success = eval_success(roll_result, d20.roll(f"{roll_data.dc}"))
        else:
            success = None
        if roll_data.discord_post:
            try:
                guild = await get_guild_by_id(roll_data.guild)
                username = get_username_by_id(roll_data.user)

                if roll_data.secret:
                    await bot.get_channel(int(guild.gm_tracker_channel)).send(
                        f"```Secret Roll from {username}```\n{roll}\n{roll_str}"
                    )
                else:
                    await bot.get_channel(int(guild.tracker_channel)).send(
                        f"```Roll from {username}```\n{roll}\n{roll_str}"
                    )
                post = True
            except Exception:
                post = False
        else:
            post = False

        output = {
            "roll": str(roll),
            "roll_result": str(roll_result),
            "total": int(roll_result.total),
            "success": success,
            "posted": post,
        }
        #
        json_op = json.dumps(output)
        print(json_op)
        # return output
        return json_op

    except Exception as e:
        logging.warning(f"API /roll: {e}")
        report = API_ErrorReport(roll_data, "dice_roller", e, bot)
        await report.report()
