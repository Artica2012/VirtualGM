import logging

from Base.Autocomplete import AutoComplete
from utils.Char_Getter import get_character
from RED.RED_Support import RED_SKills


class RED_Autocomplete(AutoComplete):
    async def macro_select(self, **kwargs):
        if "attk" in kwargs.keys():
            attk = kwargs["attk"]
        else:
            attk = False

        if "auto" in kwargs.keys():
            auto = kwargs["auto"]
        else:
            auto = False

        try:
            character = self.ctx.options["character"]
            char_split = character.split(",")
            if len(char_split) > 1:
                character = char_split[0]
        except Exception:
            return []

        print(character)
        try:
            Character_Model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
            macro_list = Character_Model.macros
            print(macro_list)

            if attk and auto:
                attk_list = Character_Model.attacks.keys()
                if self.ctx.value != "":
                    val = self.ctx.value.lower()
                    return [option.title() for option in attk_list if val in option.lower()]
                else:
                    return [option.title() for option in attk_list]

            if self.ctx.value != "":
                val = self.ctx.value.lower()
                full_list = macro_list
                skill_list = [item for item in RED_SKills.keys()]
                full_list.extend(skill_list)
                return [option.title() for option in full_list if val in option.lower()]
            else:
                if attk:
                    attk_list = Character_Model.attacks.keys()
                    return [option.title() for option in attk_list]
                return [option.title() for option in macro_list]

        except Exception as e:
            logging.warning(f"RED macro_select: {e}")
            return []

    async def get_attributes(self, **kwargs):
        if "attk" in kwargs.keys():
            attk = kwargs["attk"]
        else:
            attk = False

        if "auto" in kwargs.keys():
            auto = kwargs["auto"]
        else:
            auto = False

        try:
            character = self.ctx.options["character"]
            char_split = character.split(",")
            if len(char_split) > 1:
                character = char_split[0]
        except Exception:
            return []

        print(character)
        try:
            Character_Model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
            macro_list = Character_Model.macros
            print(macro_list)

            if attk and auto:
                attk_list = Character_Model.attacks.keys()
                if self.ctx.value != "":
                    val = self.ctx.value.lower()
                    return [option.title() for option in attk_list if val in option.lower()]
                else:
                    return [option.title() for option in attk_list]

            if self.ctx.value != "":
                val = self.ctx.value.lower()
                full_list = macro_list
                skill_list = [item for item in RED_SKills.keys()]
                full_list.extend(skill_list)
                return [option.title() for option in full_list if val in option.lower()]
            else:
                if attk:
                    attk_list = Character_Model.attacks.keys()
                    return [option.title() for option in attk_list]
                return [option.title() for option in macro_list]

        except Exception as e:
            logging.warning(f"RED macro_select: {e}")
            return []
