# pf2_functions.py
import os

import d20
# define global variables
PF2_attributes = ["AC", "Fort", "Reflex", "Will", "DC"]
PF2_saves = ["Fort", "Reflex", "Will"]
PF2_base_dc = 10


def PF2_eval_succss(dice_result: d20.RollResult, goal: d20.RollResult):
    success_string = ""
    if dice_result.total >= goal.total + PF2_base_dc:
        result_tier = 4
    elif dice_result.total >= goal.total:
        result_tier = 3
    elif goal.total >= dice_result.total >= goal.total - 9:
        result_tier = 2
    else:
        result_tier = 1

    match dice_result.crit:
        case d20.CritType.CRIT:
            result_tier += 1
        case d20.CritType.FAIL:
            result_tier -= 1

    if result_tier >= 4:
        success_string = "Critical Success"
    elif result_tier == 3:
        success_string = "Success"
    elif result_tier == 2:
        success_string = "Failure"
    else:
        success_string = "Critical Failure"

    return success_string

