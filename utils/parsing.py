# For Parsing strings into dice stuff
import d20


def ParseModifiers(modifier_st: str):
    return f"{'+' if modifier_st[0] not in ['+', '-'] else ''}{modifier_st}"


def opposed_roll(roll: d20.RollResult, dc: d20.RollResult):
    return (
        f"{':thumbsup:' if roll.total >= dc.total else ':thumbsdown:'}"
        f" {roll} >= {dc} {'Success' if roll.total >= dc.total else 'Failure'}!"
    )
