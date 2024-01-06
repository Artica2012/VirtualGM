import d20

from Base.Macro import Macro
from EPF.EPF_Support import EPF_Success_colors
from PF2e.pf2_functions import PF2_eval_succss


class PF2_Macro(Macro):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)
        self.default_vars = {"u": 0, "t": 2, "e": 4, "m": 6, "l": 8}

    def opposed_roll(self, roll: d20.RollResult, dc: d20.RollResult):
        # print(f"{roll} - {dc}")
        success_string = PF2_eval_succss(roll, dc)
        color = EPF_Success_colors(success_string)
        return (
            (
                f"{':thumbsup:' if success_string == 'Critical Success' or success_string == 'Success' else ':thumbsdown:'} {roll} >="  # noqa
                f" {dc} {success_string}!"
            ),
            color,
        )
