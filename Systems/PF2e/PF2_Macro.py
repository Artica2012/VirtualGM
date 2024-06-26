import d20

from Systems.Base.Macro import Macro
from Systems.EPF.EPF_Support import EPF_Success_colors
from Systems.PF2e.pf2_functions import PF2_eval_succss, default_vars


class PF2_Macro(Macro):
    def __init__(self, ctx, guild):
        super().__init__(ctx, guild)
        self.default_vars = default_vars

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
