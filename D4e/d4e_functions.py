# pf2_functions.py


# imports

import d20

D4e_attributes = ["AC", "Fort", "Reflex", "Will"]
D4e_base_roll = d20.roll(f"{10}")


def D4e_eval_success(dice_result: d20.RollResult, goal: d20.RollResult):
    success_string = ""
    match dice_result.crit:
        case d20.CritType.CRIT:
            success_string = "Success"
        case d20.CritType.FAIL:
            success_string = "Failure"
        case _:
            success_string = "Success" if dice_result.total >= goal.total else "Failure"

    return success_string


# Builds the tracker string. Updated to work with block initiative


