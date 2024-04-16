from Systems.Base.Macro import Macro
from Systems.D4e.d4e_functions import default_vars


class D4e_Macro(Macro):
    def __init__(self, ctx, guild):
        super().__init__(ctx, guild)
        self.default_vars = default_vars
