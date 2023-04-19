import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Utilities import Utilities
from EPF.EPF_Character import get_EPF_Character
from database_models import get_tracker


class EPF_Utilities(Utilities):
    def __init__(self, ctx, guild, engine):
        super().__init__(ctx, guild, engine)

    async def add_character(self, bot, name: str, hp: int, player_bool: bool, init: str):
        await self.ctx.channel.send("Please use `/pf2 pb_import` or `/pf2 add_npc` to add a character")
        return False

    async def copy_character(self, name: str, new_name: str):
        await self.ctx.channel.send("Please use `/pf2 pb_import` or `/pf2 add_npc` to add a character")
        return False

    async def edit_attack(self, character, attack, dmg_stat, attk_stat, crit, dmg, prof):
        # print("editing attack")
        Character_Model = await get_EPF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        try:
            attack_dict = Character_Model.character_model.attacks
            # print(attack_dict)
            if dmg_stat is not None:
                attack_dict[attack]["stat"] = dmg_stat
            if attk_stat is not None:
                attack_dict[attack]["attk_stat"] = attk_stat
            if crit is not None:
                attack_dict[attack]["crit"] = crit
            if dmg is not None:
                attack_dict[attack]["dmg_type"] = dmg
            if prof is not None:
                try:
                    prof = int(prof)
                    attack_dict[attack]["override_prof"] = prof
                except Exception:
                    pass
            # print(attack_dict)
        except Exception as e:
            logging.error(f"EPF utilities edit attack (edit): {e}")
            return False
        try:
            EPF_Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            async with async_session() as session:
                query = await session.execute(select(EPF_Tracker).where(EPF_Tracker.name == character))
                query_char = query.scalars().one()

                query_char.attacks = attack_dict
                await session.commit()
            Character_Model = await get_EPF_Character(character, self.ctx, engine=self.engine, guild=self.guild)
            print(Character_Model.character_model.attacks)
            return True
        except Exception as e:
            logging.error(f"EPF utilities edit attack (write): {e}")
            return False

    async def delete_character(self, character: str):
        Character = await get_EPF_Character(character, self.ctx, engine=self.engine, guild=self.guild)
        if Character.character_model.partner is not None:
            try:
                logging.info("Eidolon/Partner Relationshio")
                Partner = await get_EPF_Character(
                    Character.character_model.partner, self.ctx, engine=self.engine, guild=self.guild
                )
                # IF The character is the Eidolon, delete its entry from its partner
                if Character.character_model.eidolon:
                    logging.info("Eidolon")
                    EPF_Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
                    async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
                    async with async_session() as session:
                        char_result = await session.execute(
                            select(EPF_Tracker).where(EPF_Tracker.name == Partner.char_name)
                        )
                        partner_object = char_result.scalars().one()
                        partner_object.partner = None
                        await session.commit()
                else:  # If its not the eidolon, then Character is the user, so delete the eidolon before
                    # deleting the character entry
                    logging.info("Partner")
                    Partner_Util = EPF_Utilities(self.ctx, self.guild, self.engine)
                    await Partner_Util.delete_character(Partner.char_name)
            except Exception as e:
                logging.exception(e)
                return False

        # Now delete the character normally
        return await super().delete_character(character)
