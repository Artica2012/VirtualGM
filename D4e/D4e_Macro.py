from Base.Macro import Macro


class D4e_Macro(Macro):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)
        self.default_vars = {"t": 5}
