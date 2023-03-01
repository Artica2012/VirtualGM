# imports
import asyncio
import datetime
import logging
import os
import inspect
import sys

import discord
import d20
import sqlalchemy as db
from discord import option, Interaction
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_, select, false, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.ddl import DropTable

import D4e.d4e_functions
import PF2e.pf2_functions
import time_keeping_functions
import ui_components
from database_models import Global
from database_models import get_tracker, get_condition, get_macro
from database_models import get_tracker_table, get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time

import warnings
from sqlalchemy import exc

class Character():
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, guild=None):
        self.char_name = char_name
        self.ctx = ctx
        self.guild = guild
        self.engine = engine
        self.id = character.id
        self.name = character.name
        self.player = character.player
        self.user = character.user
        self.current_hp = character.current_hp
        self.max_hp = character.max_hp
        self.temp_hp = character.max_hp
        self.init_string = character.init_string
        self.init = character.init
        self.character_model = character

    async def character(self):
        logging.info("Loading Character")
        if self.guild is not None:
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
        else:
            Tracker = await get_tracker(self.ctx, self.engine)
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == self.char_name))
                character = result.scalars().one()
            return character

        except NoResultFound:
            return None

    async def change_hp(self, amount: int, heal: bool):
        logging.info("Edit HP")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)
            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.name))
                character = char_result.scalars().one()

                chp = character.current_hp
                new_hp = chp
                maxhp = character.max_hp
                thp = character.temp_hp
                new_thp = 0

                # If its D4e, let the HP go below 0, but start healing form 0.
                # Bottom out at 0 for everyone else
                if heal:
                    if self.guild.system == "D4e" and chp < 0:
                        chp = 0
                    new_hp = chp + amount
                    if new_hp > maxhp:
                        new_hp = maxhp
                if not heal:
                    if thp == 0:
                        new_hp = chp - amount
                        if new_hp < 0 and self.guild.system != "D4e":
                            new_hp = 0
                    else:
                        if thp > amount:
                            new_thp = thp - amount
                            new_hp = chp
                        else:
                            new_thp = 0
                            new_hp = chp - amount + thp
                        if new_hp < 0 and self.guild.system != "D4e":
                            new_hp = 0

                character.current_hp = new_hp
                character.temp_hp = new_thp
                await session.commit()

            if character.player:  # Show the HP it its a player
                if heal:
                    await self.ctx.send_followup(f"{self.name} healed for {amount}. New HP: {new_hp}/{character.max_hp}")
                else:
                    await self.ctx.send_followup(f"{self.name} damaged for {amount}. New HP: {new_hp}/{character.max_hp}")
            else:  # Obscure the HP if its an NPC
                if heal:
                    await self.ctx.send_followup(
                        f"{self.name} healed for {amount}. {await self.calculate_hp(new_hp, character.max_hp)}")
                else:
                    await self.ctx.send_followup(
                        f"{self.name} damaged for {amount}. {await self.calculate_hp(new_hp, character.max_hp)}")
            await self.update()
            return True
        except Exception as e:
            logging.warning(f"change_hp: {e}")
            return False

    async def calculate_hp(self, chp, maxhp):
        logging.info(f"Calculate hp {chp}/{maxhp}")
        hp = chp / maxhp
        if hp == 1:
            hp_string = "Uninjured"
        elif hp > 0.5:
            hp_string = "Injured"
        elif hp >= 0.1:
            hp_string = "Bloodied"
        elif chp > 0:
            hp_string = "Critical"
        else:
            hp_string = "Dead"

        return hp_string

    async def add_thp(self, amount: int):
        logging.info(f"add_thp {amount}")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.char_name))
                character = char_result.scalars().one()
                character.temp_hp = character.temp_hp + amount
                await session.commit()
            await self.update()
            return True
        except Exception as e:
            logging.warning(f"add_thp: {e}")
            return False

    # Set the initiative
    async def set_init(self, init: int):
        logging.info(f"set_init {self.char_name} {init}")
        if self.ctx is None and self.guild is None:
            raise LookupError("No guild reference")

        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            if self.guild is None:
                Tracker = await get_tracker(self.ctx, self.engine,)
            else:
                Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            async with async_session() as session:
                char_result = await session.execute(select(Tracker).where(Tracker.name == self.char_name))
                character = char_result.scalars().one()
                character.init = init
                await session.commit()
            await self.update()
        except Exception as e:
            logging.error(f"set_init: {e}")

    async def update(self):
        logging.info(f"Updating character: {self.char_name}")
        self.character_model = await self.character()
        self.char_name = self.character_model.char_name
        self.ctx = self.character_model.ctx
        self.guild = self.character_model.guild
        self.engine = self.character_model.engine
        self.id = self.character_model.id
        self.name = self.character_model.name
        self.player = self.character_model.player
        self.user = self.character_model.user
        self.current_hp = self.character_model.current_hp
        self.max_hp = self.character_model.max_hp
        self.temp_hp = self.character_model.max_hp
        self.init_string = self.character_model.init_string
        self.init = self.character_model.init

