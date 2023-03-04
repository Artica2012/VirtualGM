import logging

import d20
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Generic.character_functions import add_character
from database_models import get_tracker
from error_handling_reporting import error_not_initialized, ErrorReport
from utils.Tracker_Getter import get_tracker_model


class Utilities():
    def __init__(self, ctx, guild, engine):
        self.ctx = ctx
        self.guild = guild
        self.engine = engine

    async def add_character(self, bot, name: str, hp: int, player_bool: bool,
                            init: str):
        logging.info("add_character")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

            initiative = 0
            if self.guild.initiative is not None:
                try:
                    roll = d20.roll(init)
                    initiative = roll.total
                except ValueError:
                    await self.ctx.channel.send(f"Invalid Initiative String `{init}`, Please check and try again.")
                    return False
                except Exception:
                    initiative = 0

            async with async_session() as session:
                Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
                async with session.begin():
                    tracker = Tracker(
                        name=name,
                        init_string=init,
                        init=initiative,
                        player=player_bool,
                        user=ctx.user.id,
                        current_hp=hp,
                        max_hp=hp,
                        temp_hp=0,
                    )
                    session.add(tracker)
                await session.commit()
            Tracker_Model = await get_tracker_model(self.ctx, bot, guild=self.guild, engine=self.engine)
            await Tracker_Model.update_pinned_tracker()
            return True
        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"add_character: {e}")
            report = ErrorReport(self.ctx, add_character.__name__, e, bot)
            await report.report()
            return False
