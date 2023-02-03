# NPC_importer.py
import functools
import logging
import os

# imports
from datetime import datetime

import discord
import asyncio
import sqlalchemy as db
from discord import option, Interaction
from discord.commands import SlashCommandGroup, option
from discord.ext import commands, tasks
from discord.ui import View
from dotenv import load_dotenv
from sqlalchemy import or_, func
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

import database_models
import initiative
from database_models import Global, Base, TrackerTable, ConditionTable, MacroTable, get_tracker_table, \
    get_condition_table, get_macro_table, get_macro, get_condition, get_tracker, NPC
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time

# define global variables

load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
    USERNAME = os.getenv('Username')
    PASSWORD = os.getenv('Password')
    HOSTNAME = os.getenv('Hostname')
    PORT = os.getenv('PGPort')
else:
    TOKEN = os.getenv('BETA_TOKEN')
    USERNAME = os.getenv('BETA_Username')
    PASSWORD = os.getenv('BETA_Password')
    HOSTNAME = os.getenv('BETA_Hostname')
    PORT = os.getenv('BETA_PGPort')

GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')
DATABASE = os.getenv('DATABASE')


async def npc_lookup(ctx: discord.ApplicationContext, engine, lookup_engine, bot, name: str, lookup: str, elite: str):
    async_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(NPC)
                                       .where(func.lower(NPC.name).contains(lookup.lower())))
        lookup_list = result.scalars().all()
    view = View()
    if len(lookup_list) == 0:
        await ctx.send_followup("Nothing Found, Try Again.")
        return False
    for item in lookup_list[:20:]:
        await asyncio.sleep(0)
        button = PF2NpcSelectButton(ctx, engine, bot, item, name, elite)
        view.add_item(button)
    await ctx.send_followup(view=view)
    # print(ctx.message.id)
    return True


class PF2NpcSelectButton(discord.ui.Button):
    def __init__(self, ctx: discord.ApplicationContext, engine, bot: discord.Bot, data, name, elite: str):
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
        self.data = data
        self.name = name
        self.elite = elite
        super().__init__(
            label=data.name,
            style=discord.ButtonStyle.primary,
        )

    async def callback(self, interaction: discord.Interaction):
        # Add the character
        print(interaction.message.id)
        message = interaction.message
        await message.delete()

        # elite/weak adjustments
        hp_mod = 0
        stat_mod = 0
        if self.elite == 'elite':
            if self.data.level <= 1:
                hp_mod = 10
            elif self.data.level <= 4:
                hp_mod = 15
            elif self.data.level <= 19:
                hp_mod = 20
            else:
                hp_mod = 30
            stat_mod = 2
        if self.elite == 'weak':
            if self.data.level <= 1:
                hp_mod = -10
            elif self.data.level <= 4:
                hp_mod = -15
            elif self.data.level <= 19:
                hp_mod = -20
            else:
                hp_mod = -30
            stat_mod = -2

        # try:
        dice = DiceRoller('')
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == self.ctx.interaction.channel_id,
                    Global.gm_tracker_channel == self.ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            print(guild.initiative)
            # print(int(self.data.init)+stat_mod)
            initiative_num = 0
            if guild.initiative != None:
                try:
                    # print(f"Init: {init}")
                    initiative_num = int(self.data.init) + stat_mod
                    print(initiative_num)
                except:
                    try:
                        if self.elite == 'weak':
                            roll = await dice.plain_roll(f"{self.data.init}{stat_mod}")
                        else:
                            roll = await dice.plain_roll(f"{self.data.init}+{stat_mod}")
                        initiative_num = roll[1]
                        print(initiative_num)
                        if type(initiative_num) != int:
                            initiative_num = 0
                    except:
                        initiative_num = 0

        async with async_session() as session:
            Tracker = await get_tracker(self.ctx, self.engine, id=guild.id)
            async with session.begin():
                tracker = Tracker(
                    name=self.name,
                    init_string=f"{self.data.init}+{stat_mod}",
                    init=initiative_num,
                    player=False,
                    user=self.ctx.user.id,
                    current_hp=self.data.hp + hp_mod,
                    max_hp=self.data.hp + hp_mod,
                    temp_hp=0
                )
                session.add(tracker)
            await session.commit()

        Condition = await get_condition(self.ctx, self.engine, id=guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
            character = char_result.scalars().one()

        async with session.begin():
            session.add(Condition(
                character_id=character.id,
                title='AC',
                number=self.data.ac + stat_mod,
                counter=True,
                visible=False))
            session.add(Condition(
                character_id=character.id,
                title='Fort',
                number=self.data.fort + stat_mod,
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Reflex',
                number=self.data.reflex + stat_mod,
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Will',
                number=self.data.will + stat_mod,
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='DC',
                number=self.data.dc + stat_mod,
                counter=True,
                visible=False
            ))
            await session.commit()

        # Parse Macros
        attack_list = self.data.macros.split('::')
        Macro = await get_macro(self.ctx, self.engine, id=guild.id)
        async with session.begin():
            for attack in attack_list[:-1]:
                await asyncio.sleep(0)
                # split the attack
                print(attack)
                split_string = attack.split(';')
                print(split_string)
                base_name = split_string[0].strip()
                attack_string = split_string[1].strip()
                damage_string = split_string[2].strip()
                if self.elite == 'weak':
                    attack_macro = Macro(
                        character_id=character.id,
                        name=f"{base_name} - Attack",
                        macro=f"{attack_string}{stat_mod}"
                    )
                else:
                    attack_macro = Macro(
                        character_id=character.id,
                        name=f"{base_name} - Attack",
                        macro=f"{attack_string}+{stat_mod}"
                    )
                session.add(attack_macro)
                print('Attack Added')
                if self.elite == 'weak':
                    damage_macro = Macro(
                        character_id=character.id,
                        name=f"{base_name} - Damage",
                        macro=f"{damage_string}{stat_mod}"
                    )
                else:
                    damage_macro = Macro(
                        character_id=character.id,
                        name=f"{base_name} - Damage",
                        macro=f"{damage_string}+{stat_mod}"
                    )

                session.add(damage_macro)
                print("Damage Added")
            await session.commit()
        print("Committed")

        async with session.begin():
            if guild.initiative != None:
                if not await initiative.init_integrity_check(self.ctx, guild.initiative, guild.saved_order,
                                                             self.engine):
                    # print(f"integrity check was false: init_pos: {guild.initiative}")
                    for pos, row in enumerate(await initiative.get_init_list(self.ctx, self.engine)):
                        await asyncio.sleep(0)
                        if row.name == guild.saved_order:
                            guild.initiative = pos
                            # print(f"integrity checked init_pos: {guild.initiative}")
                            await session.commit()

        await initiative.update_pinned_tracker(self.ctx, self.engine, self.bot)
        # view=View()
        # await interaction.message.edit("Complete", view=view)
        output_string = f"{self.data.name} added as {self.name}"

        await self.ctx.channel.send(output_string)
        # except Exception as e:
        #     await self.ctx.channel.send("Action Failed, please try again", delete_after=60)
