# imports
import asyncio
import logging

import d20
import discord
from discord import Interaction
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

import Systems.PF2e.PF2_Character
from Backend.Database.engine import async_session
from Systems.Base.Tracker import get_init_list
from Systems.Base.Utilities import Utilities
from Backend.Database.database_models import get_tracker, get_condition
from Backend.utils.error_handling_reporting import error_not_initialized, ErrorReport
from Backend.utils import utils

# from initiative import get_guild, PF2AddCharacterModal, D4eAddCharacterModal, update_pinned_tracker
from Backend.utils.Tracker_Getter import get_tracker_model
from Backend.utils.utils import get_guild


# import D4e.d4e_functions


class PF2_Utilities(Utilities):
    def __init__(self, ctx, guild):
        super().__init__(ctx, guild)

    async def add_character(self, bot, name: str, hp: int, player_bool: bool, init: str, image: str = None, **kwargs):
        if "multi" in kwargs.keys():
            multi = kwargs["multi"]
        else:
            multi = 1
        logging.info("add_character")
        try:
            pf2Modal = PF2AddCharacterModal(
                name=name,
                hp=hp,
                init=init,
                initiative=init,
                player=player_bool,
                ctx=self.ctx,
                bot=bot,
                title=name,
                pic=image,
                guild=self.guild,
                multi=multi,
            )
            await self.ctx.send_modal(pf2Modal)
            return True

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"add_character: {e}")
            report = ErrorReport(self.ctx, "add_character", e, bot)
            await report.report()
            return False


class PF2AddCharacterModal(discord.ui.Modal):
    def __init__(self, name: str, hp: int, init: str, initiative, player, ctx, bot, pic, guild, multi, *args, **kwargs):
        self.name = name
        self.hp = hp
        self.init = init
        self.initiative = initiative
        self.player = player
        self.ctx = ctx
        self.bot = bot
        self.pic = pic
        self.guild = guild
        if multi is not None:
            self.number = multi
        else:
            self.number = 1

        super().__init__(
            discord.ui.InputText(
                label="AC",
                placeholder="Armor Class",
            ),
            discord.ui.InputText(
                label="Fort",
                placeholder="Fortitude",
            ),
            discord.ui.InputText(
                label="Reflex",
                placeholder="Reflex",
            ),
            discord.ui.InputText(
                label="Will",
                placeholder="Will",
            ),
            discord.ui.InputText(
                label="Class / Spell DC",
                placeholder="DC",
            ),
            *args,
            **kwargs,
        )

    async def callback(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_message(f"{self.name} Created")
        guild = await get_guild(self.ctx, None)
        Tracker_Model = await get_tracker_model(self.ctx, guild=guild)

        for x in range(0, self.number):
            if self.number > 1:
                modifier = f" {utils.NPC_Iterator[x]}"
            else:
                modifier = ""
            name = f"{self.name} {modifier}"

            new_hp = d20.roll(f"{self.hp}").total

            initiative = 0
            if self.guild.initiative is not None:
                try:
                    roll = d20.roll(self.initiative)
                    initiative = roll.total
                except ValueError:
                    await self.ctx.channel.send(
                        f"Invalid Initiative String `{self.initiative}`, Please check and try again."
                    )
                    return False
                except Exception:
                    initiative = 0

            embed = discord.Embed(
                title="Character Created (PF2)",
                fields=[
                    discord.EmbedField(name="Name: ", value=name, inline=True),
                    discord.EmbedField(name="HP: ", value=f"{self.hp}", inline=True),
                    discord.EmbedField(name="AC: ", value=self.children[0].value, inline=True),
                    discord.EmbedField(name="Fort: ", value=self.children[1].value, inline=True),
                    discord.EmbedField(name="Reflex: ", value=self.children[2].value, inline=True),
                    discord.EmbedField(name="Will: ", value=self.children[3].value, inline=True),
                    discord.EmbedField(name="Class/Spell DC: ", value=self.children[4].value, inline=True),
                    discord.EmbedField(name="Initiative: ", value=self.init, inline=True),
                ],
                color=discord.Color.dark_gold(),
            )

            if self.pic is not None:
                embed.set_thumbnail(url=self.pic)
            else:
                embed.set_thumbnail(url=Systems.PF2e.PF2_Character.default_pic)

            async with async_session() as session:
                Tracker = await get_tracker(self.ctx, id=guild.id)
                async with session.begin():
                    tracker = Tracker(
                        name=name,
                        init_string=self.init,
                        init=initiative,
                        player=self.player,
                        user=self.ctx.user.id,
                        current_hp=new_hp,
                        max_hp=new_hp,
                        temp_hp=0,
                        pic=self.pic,
                    )
                    session.add(tracker)
                await session.commit()

            async with async_session() as session:
                result = await session.execute(select(Tracker.id).where(Tracker.name == name))
                id = result.scalars().one()
            Condition = await get_condition(self.ctx, id=guild.id)

            async with session.begin():
                session.add(
                    Condition(
                        character_id=id,
                        title="AC",
                        number=int(self.children[0].value),
                        counter=True,
                        visible=False,
                    )
                )
                session.add(
                    Condition(
                        character_id=id,
                        title="Fort",
                        number=int(self.children[1].value),
                        counter=True,
                        visible=False,
                    )
                )
                session.add(
                    Condition(
                        character_id=id,
                        title="Reflex",
                        number=int(self.children[2].value),
                        counter=True,
                        visible=False,
                    )
                )
                session.add(
                    Condition(
                        character_id=id,
                        title="Will",
                        number=int(self.children[3].value),
                        counter=True,
                        visible=False,
                    )
                )
                session.add(
                    Condition(
                        character_id=id,
                        title="DC",
                        number=int(self.children[4].value),
                        counter=True,
                        visible=False,
                    )
                )
                await session.commit()

            async with session.begin():
                if guild.initiative is not None:
                    if not await Tracker_Model.init_integrity_check(guild.initiative, guild.saved_order):
                        # print(f"integrity check was false: init_pos: {guild.initiative}")
                        for pos, row in enumerate(await get_init_list(self.ctx)):
                            await asyncio.sleep(0)
                            if row.name == guild.saved_order:
                                guild.initiative = pos
                                # print(f"integrity checked init_pos: {guild.initiative}")
                                await session.commit()

            await Tracker_Model.update()
            # await Tracker_Model.update_pinned_tracker()
            await self.ctx.channel.send(embeds=[embed])

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        logging.warning(error)
