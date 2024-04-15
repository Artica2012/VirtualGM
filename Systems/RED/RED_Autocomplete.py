import logging

from sqlalchemy import select, false
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Systems.Base.Autocomplete import AutoComplete
from Systems.RED.RED_Support import RED_SKills
from Backend.Database.database_models import get_tracker
from Backend.utils.Char_Getter import get_character


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

        if "net" in kwargs.keys():
            net = kwargs["net"]
        else:
            net = False

        try:
            character = self.ctx.options["character"]
            char_split = character.split(",")
            if len(char_split) > 1:
                character = char_split[0]
        except Exception:
            return []

        # print(character)
        try:
            Character_Model = await get_character(character, self.ctx, guild=self.guild)
            macro_list = Character_Model.macros
            # print(macro_list)

            if attk and auto:
                attk_list = Character_Model.attacks.keys()
                if self.ctx.value != "":
                    val = self.ctx.value.lower()
                    return [option.title() for option in attk_list if val in option.lower()]
                else:
                    return [option.title() for option in attk_list]
            elif net:
                net_list = Character_Model.net.keys()
                # print(net_list)
                if self.ctx.value != "":
                    val = self.ctx.value.lower()
                    return [option.title() for option in net_list if val in option.lower()]
                else:
                    return [option.title() for option in net_list]

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

        # print(character)
        try:
            Character_Model = await get_character(character, self.ctx, guild=self.guild)
            macro_list = Character_Model.macros
            # print(macro_list)

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

    async def character_select(self, **kwargs):
        if "gm" in kwargs.keys():
            gm = kwargs["gm"]
        else:
            gm = False

        if "multi" in kwargs.keys():
            multi = kwargs["multi"]
        else:
            multi = False

        if "net" in kwargs.keys():
            net = kwargs["net"]
        else:
            net = False

        logging.info("character_select")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine)
            async with async_session() as session:
                if net:
                    if gm and int(self.guild.gm) == self.ctx.interaction.user.id:
                        # print("You are the GM")
                        char_result = await session.execute(select(Tracker).order_by(Tracker.name.asc()))
                    elif not gm:
                        char_result = await session.execute(select(Tracker).order_by(Tracker.name.asc()))
                    else:
                        # print("Not the GM")
                        char_result = await session.execute(
                            select(Tracker)
                            .where(Tracker.user == self.ctx.interaction.user.id)
                            .order_by(Tracker.name.asc())
                        )

                    character_list = char_result.scalars().all()
                    # print(len(character_list))
                    character = []
                    for item in character_list:
                        # print(item.name)
                        if item.net != {}:
                            character.append(item.name)
                    # print(character)
                else:
                    if gm and int(self.guild.gm) == self.ctx.interaction.user.id:
                        # print("You are the GM")
                        char_result = await session.execute(
                            select(Tracker.name).where(Tracker.net_status == false()).order_by(Tracker.name.asc())
                        )
                    elif not gm:
                        char_result = await session.execute(
                            select(Tracker.name).where(Tracker.net_status == false()).order_by(Tracker.name.asc())
                        )
                    else:
                        # print("Not the GM")
                        char_result = await session.execute(
                            select(Tracker.name)
                            .where(Tracker.user == self.ctx.interaction.user.id)
                            .where(Tracker.net_status == false())
                            .order_by(Tracker.name.asc())
                        )
                    character = char_result.scalars().all()
                # print(len(character))
            if self.ctx.value != "":
                val = self.ctx.value.lower()
                if multi and val[-1] == ",":
                    return [f"{val.title()} {option}" for option in character]
                return [option for option in character if val in option.lower()]
            return character
        except NoResultFound:
            return []
        except Exception as e:
            logging.warning(f"epf character_select: {e}")
            return []
