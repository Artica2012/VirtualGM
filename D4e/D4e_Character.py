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
from D4e.d4e_functions import edit_stats

import time_keeping_functions
import ui_components
from utils.utils import get_guild
from database_models import Global
from database_models import get_tracker, get_condition, get_macro
from database_models import get_tracker_table, get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time
from Generic.Character import Character
from utils.Char_Getter import get_character
from database_operations import USERNAME, PASSWORD, HOSTNAME, PORT, SERVER_DATA

import warnings
from sqlalchemy import exc

async def get_D4e_Character(char_name, ctx, guild=None, engine=None):
    logging.info("Generating PF2_Character Class")
    if engine is None:
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    guild = await get_guild(ctx, guild)
    tracker = await get_character(char_name, ctx, engine=engine, guild=guild)
    condition = await get_condition(ctx, engine, id=guild.id)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(tracker).where(PF2_tracker.name == char_name))
            character = result.scalars().one()
        async with async_session() as session:
            result = await session.execute(select(condition).where(condition.id == character.id).where(condition.visible == false()))
            stats_list = result.scalars().all()
            stats = {}
            for item in stats_list:
                stats[f"{item.title}"] = item.number
            return D4e_Character(char_name, ctx, engine, character, stats, guild=guild)

    except NoResultFound:
        return None

class D4e_Character(Character):
    def __init__(self, char_name, ctx: discord.ApplicationContext, engine, character, stats, guild):
        self.ac = stats['AC']
        self.fort = stats["Fort"]
        self.reflex = stats["Reflex"]
        self.will = stats["Will"]
        super().__init__(char_name, ctx, engine, character, guild)

    async def edit_character(self,
            name: str,
            hp: int,
            init: str,
            active: bool,
            player: discord.User,
                             bot
    ):
        logging.info("edit_character")
        try:
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            Tracker = await get_tracker(self.ctx, self.engine, id=self.guild.id)

            # Give an error message if the character is the active character and making them inactive
            if self.guild.saved_order == name:
                await self.ctx.channel.send(
                    "Unable to inactivate a character while they are the active character in initiative.  Please advance"
                    " turn and try again."
                )

            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == name))
                character = result.scalars().one()

                if hp is not None:
                    character.max_hp = hp
                if init is not None:
                    character.init_string = str(init)
                if player is not None:
                    character.user = player.id
                if active is not None:
                    character.active = active
                if active is not None and self.guild.saved_order != name:
                    character.active = active

                await session.commit()


            response = await edit_stats(self.ctx, self.engine, name, bot)
            if response:
                # await update_pinned_tracker(ctx, engine, bot)
                return True
            else:
                return False
            #
            # await ctx.respond(f"Character {name} edited successfully.", ephemeral=True)
            # await update_pinned_tracker(ctx, engine, bot)
            # await engine.dispose()
            # return True

        except NoResultFound:
            await ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"add_character: {e}")
            report = ErrorReport(ctx, add_character.__name__, e, bot)
            await report.report()
            return False

