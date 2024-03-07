# For Parsing strings into dice stuff
import d20


def ParseModifiers(modifier_st: str):
    if modifier_st is None:
        return ""
    try:
        output = f"{'+' if modifier_st and modifier_st[0] not in ['+', '-', '*', '/'] else ''}{modifier_st}"
        if output == "+0" or output == "0":
            return ""
        else:
            return output
    except Exception:
        return ""


def opposed_roll(roll: d20.RollResult, dc: d20.RollResult):
    # print(f"{roll} - {dc}")
    return (
        f"{':thumbsup:' if roll.total >= dc.total else ':thumbsdown:'}"
        f" {roll} >= {dc} {'Success' if roll.total >= dc.total else 'Failure'}!"
    )


def eval_success(roll: d20.RollResult, dc: d20.RollResult):
    print(roll)
    print(dc)
    if roll.total >= dc.total:
        return True
    else:
        return False
