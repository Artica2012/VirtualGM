# initiative.py
# Initiative Tracker Module

# imports
import asyncio
import datetime
import logging
import os
import inspect
import sys

import discord
import sqlalchemy as db
from discord import option, Interaction
from discord.commands import SlashCommandGroup
from discord.ext import commands, tasks
from dotenv import load_dotenv
from sqlalchemy import or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.ddl import DropTable

import D4e.d4e_functions
import PF2e.pf2_functions
import auto_complete
import time_keeping_functions
import ui_components
from database_models import Global
from database_models import get_tracker, get_condition, get_macro
from database_models import get_tracker_table, get_condition_table, get_macro_table
from database_operations import get_asyncio_db_engine
from dice_roller import DiceRoller
from error_handling_reporting import ErrorReport, error_not_initialized
from time_keeping_functions import output_datetime, check_timekeeper, advance_time, get_time
from auto_complete import character_select, character_select_gm, cc_select, npc_select

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


#################################################################
#################################################################
# FUNCTIONS
# General Functions

# Returns the guild. Great if you just need the data, but its read only
async def get_guild(ctx, guild):
    engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    async with async_session() as session:
        if ctx == None:
            result = await session.execute(select(Global).where(
                Global.id == guild.id))
        else:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )))
        return result.scalars().one()


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# SETUP

# Set up the tracker if it does not exist
async def setup_tracker(ctx: discord.ApplicationContext, engine, bot, gm: discord.User, channel: discord.TextChannel,
                        gm_channel: discord.TextChannel, system: str):
    logging.info(f"Setup Tracker")

    # Check to make sure bot has permissions in both channels
    if not channel.can_send() or not gm_channel.can_send():
        await ctx.respond("Setup Failed. Ensure VirtualGM has message posting permissions in both channels.",
                          ephemeral=True)
        return False

    if system == 'Pathfinder 2e':
        g_system = 'PF2'
    elif system == "D&D 4e":
        g_system = 'D4e'
    else:
        g_system = None

    try:
        metadata = db.MetaData()
        # Build the row in Global first, because the other tables reference it
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            async with session.begin():
                guild = Global(
                    guild_id=ctx.guild.id,
                    time=0,
                    gm=str(gm.id),
                    tracker_channel=channel.id,
                    gm_tracker_channel=gm_channel.id,
                    system=g_system
                )
                session.add(guild)
            await session.commit()

        # Build the tracker, con and macro tables
        try:
            async with engine.begin() as conn:  # Call the tables directly to save a database call
                emp = await get_tracker_table(ctx, metadata, engine)
                con = await get_condition_table(ctx, metadata, engine)
                macro = await get_macro_table(ctx, metadata, engine)
                await conn.run_sync(metadata.create_all)

            # Update the pinned trackers
            await set_pinned_tracker(ctx, engine, bot, channel)  # set the tracker in the player channel
            await set_pinned_tracker(ctx, engine, bot, gm_channel, gm=True)  # set up the gm_track in the GM channel
        except:
            await ctx.respond("Please check permissions and try again")
            await delete_tracker(ctx, engine, bot)
            await engine.dispose()
            return False

        await engine.dispose()
        return True


    except Exception as e:
        print(f'setup_tracker: {e}')
        report = ErrorReport(ctx, setup_tracker.__name__, e, bot)
        await report.report()
        await ctx.respond("Server Setup Failed. Perhaps it has already been set up?", ephemeral=True)
        return False


# Transfer gm permissions
async def set_gm(ctx: discord.ApplicationContext, new_gm: discord.User, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )))
            guild = result.scalars().one()
            guild.gm = str(new_gm.id)  # I accidentally stored the GM as a string instead of an int initially
            # if I ever have to wipe the database, this should be changed
            await session.commit()
        await engine.dispose()

        return True
    except Exception as e:
        print(f'set_gm: {e}')
        report = ErrorReport(ctx, set_gm.__name__, e, bot)
        await report.report()
        return False


# Delete the tracker
async def delete_tracker(ctx: discord.ApplicationContext, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        # Everything in the opposite order of creation
        metadata = db.MetaData()
        # delete each table
        emp = await get_tracker_table(ctx, metadata, engine)
        con = await get_condition_table(ctx, metadata, engine)
        macro = await get_macro_table(ctx, metadata, engine)

        async with engine.begin() as conn:
            try:
                await conn.execute(DropTable(macro, if_exists=True))
            except:
                logging.warning("Unable to delete Macro Table")
            try:
                await conn.execute(DropTable(con, if_exists=True))
            except:
                logging.warning('Unable to drop Con Table')
            try:
                await conn.execute(DropTable(emp, if_exists=True))
            except:
                logging.warning("Unable to Drop Tracker Table")

        try:
            # delete the row from Global
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

            async with async_session() as session:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )))
                guild = result.scalars().one()
                await session.delete(guild)
                await session.commit()
        except Exception as e:
            print(f"guild: delete tracker: {e}")
            report = ErrorReport(ctx, "guild: delete_tracker", e, bot)
            await report.report()
        return True
    except Exception as e:
        print(f"delete tracker: {e}")
        report = ErrorReport(ctx, "delete_tracker", e, bot)
        await report.report()


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# CHARACTER MANAGEMENT

# Add a character to the database
async def add_character(ctx: discord.ApplicationContext, engine, bot, name: str, hp: int,
                        player_bool: bool, init: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    dice = DiceRoller('')
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)

        initiative = 0
        if guild.initiative != None:
            try:
                # print(f"Init: {init}")
                initiative = int(init)
            except:
                try:
                    roll = await dice.plain_roll(init)
                    initiative = roll[1]
                    if type(initiative) != int:
                        initiative = 0
                except:
                    initiative = 0

        try:
            roll_die = await dice.plain_roll(init)
        except ValueError as e:
            await ctx.channel.send("Invalid Initiative String, Please check and try again.")
            return False

        if guild.system == 'PF2':
            pf2Modal = PF2AddCharacterModal(name=name, hp=hp, init=init, initiative=initiative,
                                            player=player_bool, ctx=ctx,
                                            engine=engine, bot=bot, title=name)
            await ctx.send_modal(pf2Modal)
            return True
        elif guild.system == 'D4e':
            D4eModal = D4eAddCharacterModal(name=name, hp=hp, init=init, initiative=initiative,
                                            player=player_bool, ctx=ctx,
                                            engine=engine, bot=bot, title=name)
            await ctx.send_modal(D4eModal)
            return True
        else:
            async with async_session() as session:
                Tracker = await get_tracker(ctx, engine, id=guild.id)
                async with session.begin():
                    tracker = Tracker(
                        name=name,
                        init_string=init,
                        init=initiative,
                        player=player_bool,
                        user=ctx.user.id,
                        current_hp=hp,
                        max_hp=hp,
                        temp_hp=0
                    )
                    session.add(tracker)
                await session.commit()

            # # If we are in initiative, fix the initiative order
            # if guild.initiative != None:
            #     await fix_init_order(ctx, engine, guild=guild)

        await engine.dispose()
        await update_pinned_tracker(ctx, engine, bot)
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'add_character: {e}')
        report = ErrorReport(ctx, add_character.__name__, e, bot)
        await report.report()
        return False


# Add a character to the database
async def edit_character(ctx: discord.ApplicationContext, engine, bot, name: str, hp: int, init: str, active:bool,
                         player: discord.User, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:

        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, guild)
        Tracker = await get_tracker(ctx, engine, id=guild.id)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == name))
            character = result.scalars().one()

            if hp != None:
                character.max_hp = hp
            if init != None:
                character.init_string = str(init)
            if player != None:
                character.user = player.id
            if active != None:
                character.active=active

            await session.commit()
        if guild.system == 'PF2':
            response = await PF2e.pf2_functions.edit_stats(ctx, engine, bot, name)
            if response:
                await update_pinned_tracker(ctx, engine, bot)
                return True
            else:
                return False
        elif guild.system == 'D4e':
            response = await D4e.d4e_functions.edit_stats(ctx, engine, bot, name)
            if response:
                await update_pinned_tracker(ctx, engine, bot)
                return True
            else:
                return False
        else:
            await ctx.respond(f"Character {name} edited successfully.", ephemeral=True)
            await engine.dispose()
            return True

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'add_character: {e}')
        report = ErrorReport(ctx, add_character.__name__, e, bot)
        await report.report()
        return False


async def copy_character(ctx: discord.ApplicationContext, engine, bot, name: str, new_name: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    dice = DiceRoller('')
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        Macro = await get_macro(ctx, engine, id=guild.id)

        # Load up the old character
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == name
            ))
            character = char_result.scalars().one()

        # If initiative is active, roll initiative
        initiative = 0
        if guild.initiative != None:
            try:
                roll = await dice.plain_roll(character.init_string)
                initiative = roll[1]
                if type(initiative) != int:
                    initiative = 0
            except:
                initiative = 0

        # Copy the character over into a new character with a new name
        async with session.begin():
            new_char = Tracker(
                name=new_name,
                init_string=character.init_string,
                init=initiative,
                player=character.player,
                user=character.user,
                current_hp=character.current_hp,
                max_hp=character.max_hp,
                temp_hp=character.temp_hp
            )
            session.add(new_char)
        await session.commit()

        # Load the new character from the database, to get its ID
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == new_name
            ))
            new_character = char_result.scalars().one()

        # Copy conditions
        async with async_session() as session:
            con_result = await session.execute(select(Condition).where(
                Condition.character_id == character.id
            ).where(Condition.visible == False))
            conditions = con_result.scalars().all()

        async with session.begin():
            for condit in conditions:
                await asyncio.sleep(0)
                new_condition = Condition(
                    character_id=new_character.id,
                    counter=condit.counter,
                    title=condit.title,
                    number=condit.number,
                    auto_increment=condit.auto_increment,
                    time=condit.time,
                    visible=condit.visible,
                )
                session.add(new_condition)
            await session.commit()

        # Copy Macros
        async with async_session() as session:
            macro_result = await session.execute(select(Macro).where(
                Macro.character_id == character.id))
            macros = macro_result.scalars().all()

        async with session.begin():
            for mac in macros:
                await asyncio.sleep(0)
                new_macro = Macro(
                    character_id=new_character.id,
                    name=mac.name,
                    macro=mac.macro
                )
                session.add(new_macro)
            await session.commit()

        await engine.dispose()
        return True

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'add_character: {e}')
        report = ErrorReport(ctx, copy_character.__name__, e, bot)
        await report.report()
        return False


# Delete a character
async def delete_character(ctx: discord.ApplicationContext, character: str, engine, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        # load tables
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        Macro = await get_macro(ctx, engine, id=guild.id)

        async with async_session() as session:
            # print(character)
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            char = result.scalars().one()
            # print(char.id)
            result = await session.execute(select(Condition).where(Condition.character_id == char.id))
            Condition_list = result.scalars().all()
            # print(Condition_list)
            result = await session.execute(select(Macro).where(Macro.character_id == char.id))
            Macro_list = result.scalars().all()
        # Delete Conditions
        for con in Condition_list:
            await asyncio.sleep(0)
            async with async_session() as session:
                await session.delete(con)
                await session.commit()
        # Delete Macros
        for mac in Macro_list:
            await asyncio.sleep(0)
            async with async_session() as session:
                await session.delete(mac)
                await session.commit()
        # Delete the Character
        async with async_session() as session:
            await session.delete(char)
            await session.commit()
        await ctx.channel.send(f"{char.name} Deleted")

        await engine.dispose()
        return True
    except Exception as e:
        print(f"delete_character: {e}")
        report = ErrorReport(ctx, delete_character.__name__, e, bot)
        await report.report()
        return False


# Generate the character sheet
async def get_char_sheet(ctx: discord.ApplicationContext, engine, bot: discord.Bot, name: str, guild=None):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        # Load the tables
        if guild == None:
            guild = await get_guild(ctx, guild)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == name))
            character = result.scalars().one()
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == character.id).order_by(Condition.title.asc()))
            condition_list = result.scalars().all()

        user = bot.get_user(character.user).name
        if character.player:
            status = "PC:"
        else:
            status = 'NPC:'
        con_dict = {}

        for item in condition_list:
            con_dict[item.title] = item.number

        embed = discord.Embed(
            title=f"{name}",
            fields=[
                discord.EmbedField(
                    name="Name: ", value=character.name, inline=False
                ),
                discord.EmbedField(
                    name=status, value=user, inline=False
                ),
                discord.EmbedField(
                    name="HP: ", value=f"{character.current_hp}/{character.max_hp}: ( {character.temp_hp} Temp)",
                    inline=False
                ),
                discord.EmbedField(
                    name="Initiative: ", value=character.init_string,
                    inline=False
                ),
            ],
            color=discord.Color.dark_gold(),
        )
        condition_embed = discord.Embed(
            title=f"Conditions",
            fields=[],
            color=discord.Color.dark_teal(),
        )
        counter_embed = discord.Embed(
            title=f"Counters",
            fields=[],
            color=discord.Color.dark_magenta(),
        )

        for item in condition_list:
            await asyncio.sleep(0)
            if not item.visible:
                embed.fields.append(
                    discord.EmbedField(
                        name=item.title, value=item.number, inline=True))
            elif item.visible and not item.time:

                if not item.counter:
                    condition_embed.fields.append(
                        discord.EmbedField(
                            name=item.title, value=item.number
                        )
                    )
                elif item.counter:
                    if item.number != 0:
                        counter_embed.fields.append(
                            discord.EmbedField(
                                name=item.title, value=item.number
                            )
                        )
                    else:
                        counter_embed.fields.append(
                            discord.EmbedField(
                                name=item.title, value='_'
                            )
                        )
            elif item.visible and item.time and not item.counter:
                condition_embed.fields.append(
                    discord.EmbedField(
                        name=item.title, value=await time_keeping_functions.time_left(ctx, engine, bot, item.number)
                    )
                )

        return [embed, counter_embed, condition_embed]
    except Exception as e:
        logging.info(f"get character sheet: {e}")
        report = ErrorReport(ctx, get_char_sheet.__name__, e, bot)
        await report.report()


# Calculates the HP String
async def calculate_hp(chp, maxhp):
    logging.info(f"Calculate hp {chp}/{maxhp}")
    hp = chp / maxhp
    if hp == 1:
        hp_string = 'Uninjured'
    elif hp > .5:
        hp_string = 'Injured'
    elif hp >= .1:
        hp_string = 'Bloodied'
    elif chp > 0:
        hp_string = 'Critical'
    else:
        hp_string = 'Dead'

    return hp_string


async def add_thp(ctx: discord.ApplicationContext, engine, bot, name: str, amount: int):
    logging.info(f"add_thp {name}  {amount}")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == name
            ))
            character = char_result.scalars().one()
            character.temp_hp = character.temp_hp + amount
            await session.commit()
        await engine.dispose()
        return True
    except Exception as e:
        print(f'add_thp: {e}')
        report = ErrorReport(ctx, add_thp.__name__, e, bot)
        await report.report()
        return False


# Edit HP
async def change_hp(ctx: discord.ApplicationContext, engine, bot, name: str, amount: int, heal: bool, guild=None):
    logging.info(f"Edit HP")
    try:
        guild = await get_guild(ctx, guild)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == name
            ))
            character = char_result.scalars().one()

            chp = character.current_hp
            new_hp = chp
            maxhp = character.max_hp
            thp = character.temp_hp
            new_thp = 0

            # If its D4e, let the HP go below 0, but start healing form 0.
            # Bottom out at 0 for everyone else
            if heal:
                if guild.system == 'D4e' and chp < 0:
                    chp = 0
                new_hp = chp + amount
                if new_hp > maxhp:
                    new_hp = maxhp
            if not heal:
                if thp == 0:
                    new_hp = chp - amount
                    if new_hp < 0 and guild.system != "D4e":
                        new_hp = 0
                else:
                    if thp > amount:
                        new_thp = thp - amount
                        new_hp = chp
                    else:
                        new_thp = 0
                        new_hp = chp - amount + thp
                    if new_hp < 0 and guild.system != "D4e":
                        new_hp = 0

            character.current_hp = new_hp
            character.temp_hp = new_thp
            await session.commit()

        if character.player: # Show the HP it its a player
            if heal:
                await ctx.send_followup(f"{name} healed for {amount}. New HP: {new_hp}/{character.max_hp}")
            else:
                await ctx.send_followup(f"{name} damaged for {amount}. New HP: {new_hp}/{character.max_hp}")
        else: # Oscure the HP if its an NPC
            if heal:
                await ctx.send_followup(f"{name} healed for {amount}. {await calculate_hp(new_hp, character.max_hp)}")
            else:
                await ctx.send_followup(f"{name} damaged for {amount}. {await calculate_hp(new_hp, character.max_hp)}")
        await engine.dispose()
        return True
    except Exception as e:
        print(f'change_hp: {e}')
        report = ErrorReport(ctx, change_hp.__name__, e, bot)
        await report.report()
        return False


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# TRACKER MANAGEMENT

# Reposts new trackers in the pre-assigned channels
async def repost_trackers(ctx: discord.ApplicationContext, engine, bot):
    logging.info(f"repost_trackers")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, None)
        channel = bot.get_channel(guild.tracker_channel)
        gm_channel = bot.get_channel(guild.gm_tracker_channel)
        await set_pinned_tracker(ctx, engine, bot, channel)  # set the tracker in the player channel
        await set_pinned_tracker(ctx, engine, bot, gm_channel, gm=True)  # set up the gm_track in the GM channel
        await engine.dispose()
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'repost_trackers: {e}')
        report = ErrorReport(ctx, repost_trackers.__name__, e, bot)
        await report.report()
        return False


# Function sets the pinned trackers and records their position in the Global table.
async def set_pinned_tracker(ctx: discord.ApplicationContext, engine, bot, channel: discord.TextChannel, gm=False):
    logging.info(f"set_pinned_tracker")
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )))
            guild = result.scalars().one()

            try:
                init_pos = int(guild.initiative)
            except Exception as e:
                init_pos = None
            display_string = await block_get_tracker(await get_init_list(ctx, engine), init_pos, ctx, engine,
                                                     bot, gm=gm)

            interaction = await bot.get_channel(channel.id).send(display_string)
            await interaction.pin()
            if gm:
                guild.gm_tracker = interaction.id
                guild.gm_tracker_channel = channel.id
            else:
                guild.tracker = interaction.id
                guild.tracker_channel = channel.id
            await session.commit()
        await engine.dispose()
        return True
    except Exception as e:
        print(f'set_pinned_tracker: {e}')
        report = ErrorReport(ctx, set_pinned_tracker.__name__, e, bot)
        await report.report()
        return False


# Set the initiative
async def set_init(ctx: discord.ApplicationContext, bot, name: str, init: int, engine, guild=None):
    logging.info(f"set_init {name} {init}")
    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        if ctx != None:
            Tracker = await get_tracker(ctx, engine)
        else:
            Tracker = await get_tracker(ctx, engine, id=guild.id)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == name
            ))
            character = char_result.scalars().one()
            character.init = init
            await session.commit()
        return True
    except Exception as e:
        logging.error(f'set_init: {e}')
        if ctx != None:
            report = ErrorReport(ctx, set_init.__name__, e, bot)
            await report.report()
        return False


# Check to make sure that the character is in the right place in initiative
async def init_integrity_check(ctx: discord.ApplicationContext, init_pos: int, current_character: str, engine,
                               guild=None):
    logging.info(f"init_integrity_check")
    init_list = await get_init_list(ctx, engine, guild=guild)
    print(init_list)
    try:
        if init_list[init_pos].name == current_character:
            return True
        else:
            return False
    except IndexError as e:
        return False
    except Exception as e:
        logging.error(f'init_integrity_check: {e}')
        return False


async def init_integrity(ctx, engine, guild=None):
    logging.info("Checking Initiative Integrity")
    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        if ctx == None:
            result = await session.execute(select(Global).where(
                Global.id == guild.id))
        else:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )))
        guild = result.scalars().one()

        if guild.initiative != None:
            if not await init_integrity_check(ctx, guild.initiative, guild.saved_order, engine):
                logging.info("Integrity Check Failed")
                logging.info(f'Integrity Info: Saved_Order {guild.saved_order}, Init Pos={guild.initiative}')
                for pos, row in enumerate(await get_init_list(ctx, engine, guild=guild)):
                    if row.name == guild.saved_order:
                        logging.info(f"name: {row.name}, saved_order: {guild.saved_order}")
                        guild.initiative = pos
                        logging.info(f"Pos: {pos}")
                        logging.info(f"New Init_pos: {guild.initiative}")
                        break # once its fixed, stop the loop because its done
        await session.commit()


# Upgraded Advance Initiative Function to work with block initiative options
async def block_advance_initiative(ctx: discord.ApplicationContext, engine, bot, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")

    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    block_done = False
    turn_list = []
    first_pass = False

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            if ctx == None:
                result = await session.execute(select(Global).where(
                    Global.id == guild.id))
            else:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )))
            guild = result.scalars().one()
            logging.info(f"BAI1: guild: {guild.id}")
            if guild.system == 'PF2' and not guild.block:
                return await pf2_advance_initiative(ctx, engine, bot, guild)

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker))
            character = char_result.scalars().all()
            logging.info(f"BAI2: characters")

            # print(f"guild.initiative: {guild.initiative}")
            if guild.initiative == None:
                dice = DiceRoller('')
                init_pos = -1
                guild.round = 1
                first_pass = True
                for char in character:
                    await asyncio.sleep(0)
                    if char.init == 0:
                        await asyncio.sleep(0)
                        try:
                            roll = await dice.plain_roll(char.init_string)
                            await set_init(ctx, bot, char.name, roll[1], engine, guild=guild)
                        except ValueError as e:
                            await set_init(ctx, bot, char.name, 0, engine, guild=guild)
            else:
                init_pos = int(guild.initiative)

        init_list = await get_init_list(ctx, engine, guild=guild)
        logging.info(f"BAI3: init_list gotten")

        if guild.saved_order == '':
            current_character = init_list[0].name
        else:
            current_character = guild.saved_order
        # Record the initial to break an infinite loop
        iterations = 0
        logging.info(f"BAI4: iteration: {iterations}")

        while not block_done:
            # make sure that the current character is at the same place in initiative as it was before
            # decrement any conditions with the decrement flag

            if guild.block:  # if in block initiative, decrement conditions at the beginning of the turn
                # if its not, set the init position to the position of the current character before advancing it
                # print("Yes guild.block")
                logging.info(f"BAI5: guild.block: {guild.block}")
                if not await init_integrity_check(ctx, init_pos, current_character, engine,
                                                  guild=guild) and not first_pass:
                    logging.info(f"BAI6: init_itegrity failied")
                    # print(f"integrity check was false: init_pos: {init_pos}")
                    for pos, row in enumerate(init_list):
                        await asyncio.sleep(0)
                        if row.name == current_character:
                            init_pos = pos
                            # print(f"integrity checked init_pos: {init_pos}")
                init_pos += 1  # increase the init position by 1
                # print(f"new init_pos: {init_pos}")
                if init_pos >= len(init_list):  # if it has reached the end, loop back to the beginning
                    init_pos = 0
                    guild.round += 1
                    if guild.timekeeping:  # if timekeeping is enable on the server
                        logging.info(f"BAI7: timekeeping")
                        # Advance time time by the number of seconds in the guild.time column. Default is 6
                        # seconds ala D&D standard
                        await advance_time(ctx, engine, bot, second=guild.time, guild=guild)
                        await check_cc(ctx, engine, bot, guild=guild)
                        logging.info(f"BAI8: cc checked")

            # Decrement the conditions
            await init_con(ctx, engine, bot, current_character, None, guild)

            if not guild.block:  # if not in block initiative, decrement the conditions at the end of the turn
                logging.info(f"BAI14: Not Block")
                # print("Not guild.block")
                # if its not, set the init position to the position of the current character before advancing it
                if not await init_integrity_check(ctx, init_pos, current_character, engine,
                                                  guild=guild) and not first_pass:
                    logging.info(f"BAI15: Integrity check failed")
                    # print(f"integrity check was false: init_pos: {init_pos}")
                    for pos, row in enumerate(init_list):
                        await asyncio.sleep(0)
                        if row.name == current_character:
                            init_pos = pos
                            # print(f"integrity checked init_pos: {init_pos}")
                init_pos += 1  # increase the init position by 1
                # print(f"new init_pos: {init_pos}")
                if init_pos >= len(init_list):  # if it has reached the end, loop back to the beginning
                    init_pos = 0
                    guild.round += 1
                    if guild.timekeeping:  # if timekeeping is enable on the server
                        # Advance time time by the number of seconds in the guild.time column. Default is 6
                        # seconds ala D&D standard
                        await advance_time(ctx, engine, bot, second=guild.time, guild=guild)
                        await check_cc(ctx, engine, bot, guild=guild)
                        logging.info(f"BAI16: cc checked")

                        # block initiative loop
            # check to see if the next character is player vs npc
            # print(init_list)
            # print(f"init_pos: {init_pos}, len(init_list): {len(init_list)}")
            if init_pos >= len(init_list) - 1:
                # print(f"init_pos: {init_pos}")
                if init_list[init_pos].player != init_list[0].player:
                    block_done = True
            elif init_list[init_pos].player != init_list[init_pos + 1].player:
                block_done = True
            if not guild.block:
                block_done = True

            turn_list.append(init_list[init_pos].name)
            current_character = init_list[init_pos].name
            iterations += 1
            if iterations >= len(init_list):  # stop an infinite loop
                block_done = True

            # print(turn_list)

        async with async_session() as session:
            if ctx == None:
                result = await session.execute(select(Global).where(
                    Global.id == guild.id))
            else:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )))
            guild = result.scalars().one()
            logging.info(f"BAI17: guild updated: {guild.id}")
            # Out side while statement - for reference
            guild.initiative = init_pos  # set it
            # print(f"final init_pos: {init_pos}")
            guild.saved_order = str(init_list[init_pos].name)
            logging.info(f"BAI18: saved order: {guild.saved_order}")
            await session.commit()
            logging.info(f"BAI19: Writted")
        await engine.dispose()
        return True
    except Exception as e:
        logging.error(f"block_advance_initiative: {e}")
        if ctx != None:
            report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
            await report.report()

# This is the code which check, decrements and removes conditions for the init next turn.
async def init_con(ctx: discord.ApplicationContext, engine, bot, current_character: str, before: bool, guild=None):
    logging.info(f"{current_character}, {before}")
    print("Decrementing Conditions")

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        if ctx == None:
            result = await session.execute(select(Global).where(
                Global.id == guild.id))
        else:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )))
        guild = result.scalars().one()

    Tracker = await get_tracker(ctx, engine, id=guild.id)
    # Run through the conditions on the current character
    try:
        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == current_character
            ))
            cur_char = char_result.scalars().one()
            logging.info(f"BAI9: cur_char: {cur_char.id}")
    except Exception as e:
        logging.error(f'advance_initiative: {e}')
        if ctx != None:
            report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
            await report.report()
        return False

    try:
        Condition = await get_condition(ctx, engine, id=guild.id)
        # con = await get_condition_table(ctx, metadata, engine)
        async with async_session() as session:
            if before != None:
                char_result = await session.execute(select(Condition)
                                                    .where(Condition.character_id == cur_char.id)
                                                    .where(Condition.flex == before)
                                                    .where(Condition.auto_increment == True)
                                                    )
            else:
                char_result = await session.execute(select(Condition)
                                                    .where(Condition.character_id == cur_char.id)
                                                    .where(Condition.auto_increment == True)
                                                    )
            con_list = char_result.scalars().all()
            logging.info(f"BAI9: condition's retrieved")
            print('First Con List')

        for con_row in con_list:
            logging.info(f"BAI10: con_row: {con_row.title} {con_row.id}")
            await asyncio.sleep(0)
            async with async_session() as session:
                result = await session.execute(select(Condition).where(Condition.id == con_row.id))
                selected_condition = result.scalars().one()
                if not selected_condition.time:  # If auto-increment and NOT time
                    if selected_condition.number >= 2:  # if number >= 2
                        selected_condition.number -= 1
                    else:
                        await session.delete(selected_condition)
                        # await session.commit()
                        logging.info(f"BAI11: Condition Deleted")
                        if ctx != None:
                            await ctx.channel.send(f"{con_row.title} removed from {cur_char.name}")
                        else:
                            tracker_channel = bot.get_channel(guild.tracker_channel)
                            tracker_channel.send(f"{con_row.title} removed from {cur_char.name}")
                    await session.commit()
                elif selected_condition.time:  # If time is true
                    await check_cc(ctx, engine, bot, guild=guild)

    except Exception as e:
        logging.error(f'block_advance_initiative: {e}')
        if ctx != None:
            report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
            await report.report()


# Upgraded Advance Initiative Function to work with block initiative options
async def pf2_advance_initiative(ctx: discord.ApplicationContext, engine, bot, guild=None):
    logging.info(f"pf2_advance_initiative")

    # Get the Guild Data
    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    first_pass = False

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            if ctx == None:
                result = await session.execute(select(Global).where(
                    Global.id == guild.id))
            else:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )))
            guild = result.scalars().one()
            logging.info(f"BAI1: guild: {guild.id}")

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        async with async_session() as session:
            char_result = await session.execute(select(Tracker))
            character = char_result.scalars().all()
            logging.info(f"BAI2: characters")

            # print(f"guild.initiative: {guild.initiative}")
            if guild.initiative == None:
                dice = DiceRoller('')
                init_pos = -1
                guild.round = 1
                first_pass = True
                for char in character:
                    await asyncio.sleep(0)
                    if char.init == 0:
                        await asyncio.sleep(0)
                        try:
                            roll = await dice.plain_roll(char.init_string)
                            await set_init(ctx, bot, char.name, roll[1], engine, guild=guild)
                        except ValueError as e:
                            await set_init(ctx, bot, char.name, 0, engine, guild=guild)
            else:
                init_pos = int(guild.initiative)

        init_list = await get_init_list(ctx, engine, guild=guild)
        logging.info(f"BAI3: init_list gotten")

        if guild.saved_order == '':
            current_character = init_list[0].name
        else:
            current_character = guild.saved_order

        # Process the conditions with the after trait (Flex = False) for the current character
        await init_con(ctx, engine, bot, current_character, False, guild=guild)

        # Advance the Turn
        # Check to make sure the init list hasn't changed, if so, correct it
        if not await init_integrity_check(ctx, init_pos, current_character, engine,
                                          guild=guild) and not first_pass:
            logging.info(f"BAI6: init_itegrity failied")
            # print(f"integrity check was false: init_pos: {init_pos}")
            for pos, row in enumerate(init_list):
                await asyncio.sleep(0)
                if row.name == current_character:
                    init_pos = pos
                    # print(f"integrity checked init_pos: {init_pos}")

        # Increase the initiative positing by 1
        init_pos += 1  # increase the init position by 1
        # print(f"new init_pos: {init_pos}")
        # If we have exceeded the end of the list, then loop back to the beginning
        if init_pos >= len(init_list):  # if it has reached the end, loop back to the beginning
            init_pos = 0
            guild.round += 1
            if guild.timekeeping:  # if timekeeping is enable on the server
                logging.info(f"BAI7: timekeeping")
                # Advance time time by the number of seconds in the guild.time column. Default is 6
                # seconds ala D&D standard
                await advance_time(ctx, engine, bot, second=guild.time, guild=guild)
                await check_cc(ctx, engine, bot, guild=guild)
                logging.info(f"BAI8: cc checked")

        current_character = init_list[init_pos].name  # Update the new current_character

        # Delete the before conditions on the new current_character
        await init_con(ctx, engine, bot, current_character, True, guild=guild)

        # Write the updates to the database
        async with async_session() as session:
            if ctx == None:
                result = await session.execute(select(Global).where(
                    Global.id == guild.id))
            else:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )))
            guild = result.scalars().one()
            logging.info(f"BAI17: guild updated: {guild.id}")
            # Out side while statement - for reference
            guild.initiative = init_pos  # set it
            # print(f"final init_pos: {init_pos}")
            guild.saved_order = str(init_list[init_pos].name)
            logging.info(f"BAI18: saved order: {guild.saved_order}")
            await session.commit()
            logging.info(f"BAI19: Writted")
        await engine.dispose()
        return True
    except Exception as e:
        logging.error(f"block_advance_initiative: {e}")
        if ctx != None:
            report = ErrorReport(ctx, block_advance_initiative.__name__, e, bot)
            await report.report()


# Returns the tracker list sorted by initiative
async def get_init_list(ctx: discord.ApplicationContext, engine, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")

    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    try:
        if guild != None:
            try:
                Tracker = await get_tracker(ctx, engine, id=guild.id)
            except:
                Tracker = await get_tracker(ctx, engine)
        else:
            Tracker = await get_tracker(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker)
                                           .where(Tracker.active == True)
                                           .order_by(Tracker.init.desc())
                                           .order_by(Tracker.id.desc()))
            init_list = result.scalars().all()
            logging.info(f"GIL: Init list gotten")
            # print(init_list)
        await engine.dispose()
        return init_list

    except Exception as e:
        logging.error("error in get_init_list")
        return []

# Returns the tracker list sorted by initiative
async def get_inactive_list(ctx: discord.ApplicationContext, engine, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")

    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    try:
        if guild != None:
            try:
                Tracker = await get_tracker(ctx, engine, id=guild.id)
            except:
                Tracker = await get_tracker(ctx, engine)
        else:
            Tracker = await get_tracker(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker)
                                           .where(Tracker.active == False)
                                           .order_by(Tracker.init.desc())
                                           .order_by(Tracker.id.desc()))
            init_list = result.scalars().all()
            logging.info(f"GIL: Init list gotten")
            # print(init_list)
        await engine.dispose()
        return init_list

    except Exception as e:
        logging.error("error in get_init_list")
        return []

# Switching function for system specific trackers
async def block_get_tracker(init_list: list, selected: int, ctx: discord.ApplicationContext, engine, bot,
                            gm: bool = False, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    async with async_session() as session:
        if ctx == None:
            result = await session.execute(select(Global).where(
                Global.id == guild.id))
        else:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )))
        guild = result.scalars().one()
        logging.info(f"BGT: Guild: {guild.id}")

        if guild.system == 'PF2':
            logging.info('PF2')
            output_string = await PF2e.pf2_functions.pf2_get_tracker(init_list, selected, ctx, engine, bot, gm,
                                                                     guild=guild)
        elif guild.system == "D4e":
            logging.info('D4e')
            output_string = await D4e.d4e_functions.d4e_get_tracker(init_list, selected, ctx, engine, bot, gm,
                                                                    guild=guild)
        else:
            logging.info('generic')
            output_string = await generic_block_get_tracker(init_list, selected, ctx, engine, bot, gm, guild=guild)
        return output_string


# Builds the tracker string. Updated to work with block initiative
async def generic_block_get_tracker(init_list: list, selected: int, ctx: discord.ApplicationContext, engine,
                                    bot, gm: bool = False, guild=None):
    logging.info(f"generic_block_get_tracker")
    guild = await get_guild(ctx, guild)
    logging.info(f"BGT1: Guild: {guild.id}")

    # Get the datetime
    datetime_string = ''
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Get the turn List for Block Initiative
    if guild.block and guild.initiative != None:
        turn_list = await get_turn_list(ctx, engine, bot, guild=guild)
        block = True
    else:
        block = False
    logging.info(f"BGT2: round: {guild.round}")

    # Code for appending the inactive list onto the init_list
    active_length = len(init_list)
    # print(f'Active Length: {active_length}')
    inactive_list = await get_inactive_list(ctx, engine, guild)
    if len(inactive_list) > 0:
        init_list.extend(inactive_list)
        # print(f'Total Length: {len(init_list)}')

    # Generate the data_time string if timekeeper is active
    try:
        if await check_timekeeper(ctx, engine, guild=guild):
            datetime_string = f" {await output_datetime(ctx, engine, bot, guild=guild)}\n" \
                              f"________________________\n"
    except NoResultFound as e:
        if ctx != None:
            await ctx.channel.send(
                error_not_initialized,
                delete_after=30)
        logging.info("Channel Not Set Up")
    except Exception as e:
        logging.error(f'get_tracker: {e}')
        report = ErrorReport(ctx, "get_tracker", e, bot)
        await report.report()

    try:
        Condition = await get_condition(ctx, engine, id=guild.id)

        # if round = 0, were not in initiative, and act accordingly
        if guild.round != 0:
            round_string = f"Round: {guild.round}"
        else:
            round_string = ""

        output_string = f"```{datetime_string}" \
                        f"Initiative: {round_string}\n"
        # Iterate through the init list
        for x, row in enumerate(init_list):
            logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
            # If there is an inactive list, and this is at the transition, place the line marker
            if len(init_list) > active_length and x == active_length:
                output_string += '-----------------\n' #Put in the divider
            # print(f'row.id= {row.id}')

            #Get all of the visible condition for the character
            async with async_session() as session:
                result = await session.execute(select(Condition)
                                               .where(Condition.character_id == row.id)
                                               .where(Condition.visible == True))
                condition_list = result.scalars().all()

            await asyncio.sleep(0) #ensure the loop doesn't lock the bot in case of an error
            sel_bool = False
            selector = ''

            # don't show an init if not in combat
            if row.init == 0 or row.active == False:
                init_string = ""
            else:
                init_string = f"{row.init}"

            if block:
                for character in turn_list: #ignore this error, turn list is gotten if block is true, so this will always apply
                    # print(f'character.id = {character.id}')
                    if row.id == character.id:
                        sel_bool = True
            else:
                if x == selected:
                    sel_bool = True

            # print(f"{row['name']}: x: {x}, selected: {selected}")

            if sel_bool:
                selector = '>>'
            if row.player or gm:
                if row.temp_hp != 0:
                    string = f"{selector}  {init_string} {str(row.name).title()}: {row.current_hp}/{row.max_hp} ({row.temp_hp}) Temp\n"
                else:
                    string = f"{selector}  {init_string} {str(row.name).title()}: {row.current_hp}/{row.max_hp}\n"
            else:
                hp_string = await calculate_hp(row.current_hp, row.max_hp)
                string = f"{selector}  {init_string} {str(row.name).title()}: {hp_string} \n"
            output_string += string

            for con_row in condition_list:
                # print(f'con_row.id = {con_row.id}')
                logging.info(f"BGT5: con_row in condition list {con_row.title} {con_row.id}")
                # print(con_row)
                await asyncio.sleep(0)
                if gm or not con_row.counter:
                    if con_row.number != None and con_row.number > 0:
                        if con_row.time:
                            time_stamp = datetime.datetime.fromtimestamp(con_row.number)
                            current_time = await get_time(ctx, engine, bot, guild=guild)
                            time_left = time_stamp - current_time
                            days_left = time_left.days
                            processed_minutes_left = divmod(time_left.seconds, 60)[0]
                            processed_seconds_left = divmod(time_left.seconds, 60)[1]
                            if processed_seconds_left < 10:
                                processed_seconds_left = f"0{processed_seconds_left}"
                            if days_left != 0:
                                con_string = f"       {con_row.title}: {days_left} Days, {processed_minutes_left}:{processed_seconds_left}\n "
                            else:
                                con_string = f"       {con_row.title}: {processed_minutes_left}:{processed_seconds_left}\n"
                        else:
                            con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = f"       {con_row.title}\n"

                elif con_row.counter == True and sel_bool and row.player:
                    con_string = f"       {con_row.title}: {con_row.number}\n"
                else:
                    con_string = ''
                output_string += con_string

        output_string += f"```"
        # print(output_string)
        await engine.dispose()
        return output_string
    except Exception as e:
        logging.info(f"block_get_tracker 2: {e}")
        report = ErrorReport(ctx, block_get_tracker.__name__, e, bot)
        await report.report()


# Gets the locations of the pinned trackers, then updates them with the newest tracker
async def update_pinned_tracker(ctx: discord.ApplicationContext, engine, bot, guild=None):
    logging.info(f"update_pinned_tracker")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    guild = await get_guild(ctx, guild) # get the guild
    logging.info(f"UPT1: Guild: {guild.id}")

    # Get the tracker messages
    tracker = guild.tracker
    tracker_channel = guild.tracker_channel
    gm_tracker = guild.gm_tracker
    gm_tracker_channel = guild.gm_tracker_channel

    # Fix the Tracker if needed
    await init_integrity(ctx, engine, guild=guild)

    try:
        # Re-acquire the tracker after the fix
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                Global.id == guild.id))
            guild = result.scalars().one()
            logging.info(f"saved_order: {guild.saved_order}")
            logging.info(f"init_pos: {guild.initiative}")

            # If in initiative, update the active tracker
            if guild.last_tracker != None:
                await block_update_init(ctx, guild.last_tracker, engine, bot, guild=guild)

            # Update the Pinned tracker
            if tracker is not None:
                tracker_display_string = await block_get_tracker(await get_init_list(ctx, engine, guild=guild),
                                                                 guild.initiative,
                                                                 ctx, engine, bot, guild=guild)
                channel = bot.get_channel(tracker_channel)
                message = await channel.fetch_message(tracker)
                await message.edit(tracker_display_string)
                logging.info(f"UPT2: tracker updated")

            # Update the GM tracker
            if gm_tracker is not None:
                gm_tracker_display_string = await block_get_tracker(await get_init_list(ctx, engine, guild=guild),
                                                                    guild.initiative,
                                                                    ctx, engine, bot, gm=True, guild=guild)
                gm_channel = bot.get_channel(gm_tracker_channel)
                gm_message = await gm_channel.fetch_message(gm_tracker)
                await gm_message.edit(gm_tracker_display_string)
                logging.info(f"UPT3: gm tracker updated")
    except NoResultFound as e:
        if ctx != None:
            await ctx.channel.send(
                error_not_initialized,
                delete_after=30)
    except Exception as e:
        logging.error(f'update_pinned_tracker: {e}')
        report = ErrorReport(ctx, update_pinned_tracker.__name__, e, bot)
        await report.report()

# Post a new initiative tracker and updates the pinned trackers
async def block_post_init(ctx: discord.ApplicationContext, engine, bot: discord.Bot, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    # Query the initiative position for the tracker and post it


    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, guild)
        logging.info(f"BPI1: guild: {guild.id}")

        if guild.block:
            turn_list = await get_turn_list(ctx, engine, bot, guild=guild)
            block = True
            # print(f"block_post_init: \n {turn_list}")
        else:
            block = False

        init_list = await get_init_list(ctx, engine, guild=guild)
        print(init_list)
        tracker_string = await block_get_tracker(init_list, guild.initiative, ctx, engine, bot, guild=guild)
        print(tracker_string)
        try:
            logging.info(f"BPI2")
            ping_string = ''
            if block:
                for character in turn_list:
                    await asyncio.sleep(0)
                    user = bot.get_user(character.user)
                    ping_string += f"{user.mention}, it's your turn.\n"
            else:
                user = bot.get_user(init_list[guild.initiative].user)
                ping_string += f"{user.mention}, it's your turn.\n"
        except Exception as e:
            # print(f'post_init: {e}')
            ping_string = ''

        # Check for systems:
        if guild.system == 'D4e':
            logging.info(f"BPI3: d4e")
            # view = await D4e.d4e_functions.D4eTrackerButtons(ctx, bot, guild, init_list)
            view = await D4e.d4e_functions.D4eTrackerButtonsIndependent(bot, guild)
            print('Buttons Generated')
            view.add_item(ui_components.InitRefreshButton(ctx, bot, guild=guild))
            view.add_item(ui_components.NextButton(bot, guild=guild))

            if ctx != None:
                if ctx.channel.id == guild.tracker_channel:

                    tracker_msg = await ctx.send_followup(f"{tracker_string}\n"
                                                          f"{ping_string}", view=view)
                else:
                    await bot.get_channel(guild.tracker_channel).send(f"{tracker_string}\n"
                                                                      f"{ping_string}", view=view, )
                    tracker_msg = await ctx.send_followup("Initiative Advanced.")
                    logging.info(f"BPI4")
            else:
                tracker_msg = await bot.get_channel(guild.tracker_channel).send(f"{tracker_string}\n"
                                                                                f"{ping_string}", view=view, )
                logging.info("BPI4 Guild")
        else:
            view = discord.ui.View(timeout=None)
            view.add_item(ui_components.InitRefreshButton(ctx, bot, guild=guild))
            view.add_item(ui_components.NextButton(bot, guild=guild))
            # Always post the tracker to the player channel
            if ctx != None:
                if ctx.channel.id == guild.tracker_channel:
                    tracker_msg = await ctx.send_followup(f"{tracker_string}\n"
                                                          f"{ping_string}", view=view)
                else:
                    await bot.get_channel(guild.tracker_channel).send(f"{tracker_string}\n"
                                                                      f"{ping_string}", view=view)
                    tracker_msg = await ctx.send_followup("Initiative Advanced.")
                    logging.info(f"BPI5")
            else:
                tracker_msg = await bot.get_channel(guild.tracker_channel).send(f"{tracker_string}\n"
                                                                                f"{ping_string}", view=view)
                logging.info(f"BPI5 Guild")
        if guild.tracker is not None:
            channel = bot.get_channel(guild.tracker_channel)
            message = await channel.fetch_message(guild.tracker)
            await message.edit(content=tracker_string)
        if guild.gm_tracker is not None:
            gm_tracker_display_string = await block_get_tracker(init_list, guild.initiative,
                                                                ctx, engine, bot, gm=True, guild=guild)
            gm_channel = bot.get_channel(guild.gm_tracker_channel)
            gm_message = await gm_channel.fetch_message(guild.gm_tracker)
            await gm_message.edit(content=gm_tracker_display_string)

        async with async_session() as session:
            if ctx == None:
                result = await session.execute(select(Global).where(
                    Global.id == guild.id))
            else:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )))
            guild = result.scalars().one()
            print(f"Saved last tracker: {guild.last_tracker}")
            # old_tracker = guild.last_tracker
            try:
                if guild.last_tracker != None:
                    tracker_channel = bot.get_channel(guild.tracker_channel)
                    old_tracker_msg = await tracker_channel.fetch_message(guild.last_tracker)
                    await old_tracker_msg.edit(view=None)
            except Exception as e:
                print(e)
            guild.last_tracker = tracker_msg.id
            print()
            await session.commit()

        await engine.dispose()
    except NoResultFound as e:
        if ctx != None:
            await ctx.channel.send(error_not_initialized,
                                   delete_after=30)
    except Exception as e:
        logging.error(f"block_post_init: {e}")
        if ctx != None:
            report = ErrorReport(ctx, block_post_init.__name__, e, bot)
            await report.report()

# Updates the active initiative tracker (not the pinned tracker)
async def block_update_init(ctx: discord.ApplicationContext, edit_id, engine,
                            bot: discord.Bot, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")

    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    # Query the initiative position for the tracker and post it
    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        guild = await get_guild(ctx, guild)
        logging.info(f"BPI1: guild: {guild.id}")
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        if guild.block:
            print(guild.id)
            turn_list = await get_turn_list(ctx, engine, bot, guild=guild)
            block = True
            # print(f"block_post_init: \n {turn_list}")
        else:
            block = False

        init_list = await get_init_list(ctx, engine, guild=guild)
        tracker_string = await block_get_tracker(init_list, guild.initiative, ctx, engine, bot, guild=guild)
        try:
            logging.info(f"BPI2")
            ping_string = ''
            if block:
                for character in turn_list:
                    await asyncio.sleep(0)
                    user = bot.get_user(character.user)
                    ping_string += f"{user.mention}, it's your turn.\n"
            else:
                user = bot.get_user(init_list[guild.initiative].user)
                ping_string += f"{user.mention}, it's your turn.\n"
        except Exception as e:
            # print(f'post_init: {e}')
            ping_string = ''
        view = discord.ui.View(timeout=None)
        # Check for systems:
        if guild.system == 'D4e':
            logging.info(f"BPI3: d4e")

            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.name == init_list[guild.initiative].name))
                char = result.scalars().one()
            async with async_session() as session:
                result = await session.execute(select(Condition)
                                               .where(Condition.character_id == char.id)
                                               .where(Condition.flex == True))
                conditions = result.scalars().all()
            for con in conditions:
                new_button = D4e.d4e_functions.D4eConditionButton(
                    con,
                    ctx, engine, bot,
                    char, guild=guild
                )
                view.add_item(new_button)
            view.add_item(ui_components.InitRefreshButton(ctx, bot, guild=guild))
            view.add_item((ui_components.NextButton(bot, guild=guild)))
            tracker_channel = bot.get_channel(guild.tracker_channel)
            edit_message = await tracker_channel.fetch_message(edit_id)
            await edit_message.edit(content=f"{tracker_string}\n"
                                    f"{ping_string}", view=view, )

        else:
            view.add_item(ui_components.InitRefreshButton(ctx, bot, guild=guild))
            view.add_item((ui_components.NextButton(bot, guild=guild)))
            tracker_channel = bot.get_channel(guild.tracker_channel)
            edit_message = await tracker_channel.fetch_message(edit_id)
            await edit_message.edit(content=f"{tracker_string}\n"
                                    f"{ping_string}", view=view, )
        if guild.tracker is not None:
            channel = bot.get_channel(guild.tracker_channel)
            message = await channel.fetch_message(guild.tracker)
            await message.edit(content=tracker_string)
        if guild.gm_tracker is not None:
            gm_tracker_display_string = await block_get_tracker(init_list, guild.initiative,
                                                                ctx, engine, bot, gm=True, guild=guild)
            gm_channel = bot.get_channel(guild.gm_tracker_channel)
            gm_message = await gm_channel.fetch_message(guild.gm_tracker)
            await gm_message.edit(content=gm_tracker_display_string)

        await engine.dispose()
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
    except Exception as e:
        logging.error(f"block_update_init: {e}")
        report = ErrorReport(ctx, block_update_init.__name__, e, bot)
        await report.report()


# Note: Works backwards
async def get_turn_list(ctx: discord.ApplicationContext, engine, bot, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    turn_list = []
    block_done = False
    if ctx == None and guild == None:
        raise LookupError("No guild reference")

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            if ctx == None:
                result = await session.execute(select(Global).where(
                    Global.id == guild.id))
            else:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )))
            guild = result.scalars().one()

            logging.info(f"GTL1: guild: {guild.id}")
            iteration = 0
            init_pos = guild.initiative
            # print(f"init_pos: {init_pos}")
            # print(init_pos)
            init_list = await get_init_list(ctx, engine, guild=guild)
            length = len(init_list)
            while not block_done:
                turn_list.append(init_list[init_pos])
                # print(f"init_pos: {init_pos}, turn_list: {turn_list}")
                player_status = init_list[init_pos].player
                if init_pos == 0:
                    if player_status != init_list[length - 1].player:
                        block_done = True
                else:
                    if player_status != init_list[init_pos - 1].player:
                        block_done = True

                init_pos -= 1
                if init_pos < 0:
                    if guild.round != 1:  # Don't loop back to the end on the first round
                        init_pos = length - 1
                    else:
                        block_done = True
                iteration += 1
                if iteration >= length:
                    block_done = True
            await engine.dispose()
            logging.info(f"GTL2 {turn_list}")
            return turn_list
    except Exception as e:
        print(f'get_turn_list: {e}')
        report = ErrorReport(ctx, get_turn_list.__name__, e, bot)
        await report.report()
        return False


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# COUNTER/CONDITION MANAGEMENT

async def set_cc(ctx: discord.ApplicationContext, engine, character: str, title: str, counter: bool, number: int,
                 unit: str, auto_decrement: bool, bot, flex: bool = False, ):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    # Get the Character's data

    try:
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'set_cc: {e}')
        report = ErrorReport(ctx, set_cc.__name__, e, bot)
        await report.report()
        return False

    try:
        if not guild.timekeeping or unit == 'Round':
            async with session.begin():
                condition = Condition(
                    character_id=character.id,
                    title=title,
                    number=number,
                    counter=counter,
                    auto_increment=auto_decrement,
                    time=False,
                    flex=flex
                )
                session.add(condition)
            await session.commit()

            await update_pinned_tracker(ctx, engine, bot)
            await engine.dispose()
            return True

        else:
            current_time = await get_time(ctx, engine, bot)
            if unit == 'Minute':
                end_time = current_time + datetime.timedelta(minutes=number)
            elif unit == 'Hour':
                end_time = current_time + datetime.timedelta(hours=number)
            else:
                end_time = current_time + datetime.timedelta(days=number)

            timestamp = end_time.timestamp()

            async with session.begin():
                condition = Condition(
                    character_id=character.id,
                    title=title,
                    number=timestamp,
                    counter=counter,
                    auto_increment=True,
                    time=True
                )
                session.add(condition)
            await session.commit()
            await update_pinned_tracker(ctx, engine, bot)
            await engine.dispose()
            return True


    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'set_cc: {e}')
        report = ErrorReport(ctx, set_cc.__name__, e, bot)
        await report.report()
        return False


async def edit_cc_interface(ctx: discord.ApplicationContext, engine, character: str, condition: str, bot, guild=None):
    logging.info("edit_cc_interface")
    view = discord.ui.View()
    try:
        guild = await get_guild(ctx, guild)
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            char = result.scalars().one()
            print(char.name)
    except NoResultFound as e:
        if ctx != None:
            await ctx.channel.send(error_not_initialized,
                                   delete_after=30)
        return [None, None]
    except Exception as e:
        logging.info(f'edit_cc: {e}')
        if ctx != None:
            report = ErrorReport(ctx, edit_cc_interface.__name__, e, bot)
            await report.report()
        return [None, None]
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == char.id).where(Condition.title == condition))
            cond = result.scalars().one()

            if cond.time or cond.number == None:
                await ctx.send_followup("Unable to edit. Try again in a future update.",
                                        ephemeral=True)
                return [None, None]
            else:
                output_string = f"{cond.title}: {cond.number}"
                view.add_item(ui_components.ConditionMinus(ctx, bot, character, condition, guild))
                view.add_item(ui_components.ConditionAdd(ctx, bot, character, condition, guild))
                return output_string, view
    except NoResultFound as e:
        if ctx != None:
            await ctx.channel.send(error_not_initialized,
                                   delete_after=30)
        return [None, None]
    except Exception as e:
        logging.info(f'edit_cc: {e}')
        if ctx != None:
            report = ErrorReport(ctx, edit_cc_interface.__name__, e, bot)
            await report.report()
        return [None, None]


async def edit_cc(ctx: discord.ApplicationContext, engine, character: str, condition: str, value: int, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        Tracker = await get_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'edit_cc: {e}')
        report = ErrorReport(ctx, edit_cc.__name__, e, bot)
        await report.report()
        return False

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == character.id).where(Condition.title == condition))
            condition = result.scalars().one()

            if condition.time:
                await ctx.send_followup("Unable to edit time based conditions. Try again in a future update.",
                                        ephemeral=True)
                return False
            else:
                condition.number = value
                await session.commit()
        await update_pinned_tracker(ctx, engine, bot)
        await engine.dispose()
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'edit_cc: {e}')
        report = ErrorReport(ctx, edit_cc.__name__, e, bot)
        await report.report()
        return False


async def increment_cc(ctx: discord.ApplicationContext, engine, character: str, condition: str, add: bool, bot,
                       guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        guild = await get_guild(ctx, guild)

        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        logging.info(f'edit_cc: {e}')
        if ctx != None:
            report = ErrorReport(ctx, increment_cc.__name__, e, bot)
            await report.report()
        return False

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == character.id).where(Condition.title == condition))
            condition = result.scalars().one()
            current_value = condition.number

            if condition.time or condition.number == None:
                await ctx.send_followup("Unable to edit. Try again in a future update.",
                                        ephemeral=True)
                return False
            else:
                if add == True:
                    condition.number = current_value + 1
                else:
                    condition.number = current_value - 1
                await session.commit()
        # await update_pinned_tracker(ctx, engine, bot)
        await engine.dispose()
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'edit_cc: {e}')
        report = ErrorReport(ctx, edit_cc.__name__, e, bot)
        await report.report()
        return False


async def delete_cc(ctx: discord.ApplicationContext, engine, character: str, condition, bot):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        Tracker = await get_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'delete_cc: {e}')
        report = ErrorReport(ctx, delete_cc.__name__, e, bot)
        await report.report()
        return False

    try:
        async with async_session() as session:
            result = await session.execute(select(Condition)
                                           .where(Condition.character_id == character.id)
                                           .where(Condition.visible == True)
                                           .where(Condition.title == condition))
            con_list = result.scalars().all()
        if len(con_list) == 0:
            await engine.dispose()
            return False

        for con in con_list:
            await asyncio.sleep(0)
            async with async_session() as session:
                await session.delete(con)
                await session.commit()

        await update_pinned_tracker(ctx, engine, bot)
        await engine.dispose()
        return True
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'delete_cc: {e}')
        report = ErrorReport(ctx, delete_cc.__name__, e, bot)
        await report.report()
        return False


async def get_cc(ctx: discord.ApplicationContext, engine, bot, character: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    Tracker = await get_tracker(ctx, engine)
    Condition = await get_condition(ctx, engine)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(Tracker).where(Tracker.name == character))
            character = result.scalars().one()

    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'get_cc: {e}')
        report = ErrorReport(ctx, get_cc.__name__, e, bot)
        await report.report()

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Condition).where(Condition.character_id == character.id).where(Condition.counter == True))
            counters = result.scalars().all()

        await engine.dispose()
        return counters
    except NoResultFound as e:
        await ctx.channel.send(error_not_initialized,
                               delete_after=30)
        return False
    except Exception as e:
        print(f'get_cc: {e}')
        report = ErrorReport(ctx, get_cc.__name__, e, bot)
        await report.report()


# Check to see if any time duration conditions have expired.
# Intended to be called when time is advanced
async def check_cc(ctx: discord.ApplicationContext, engine, bot, guild=None):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    current_time = await get_time(ctx, engine, bot, guild=guild)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    if ctx != None:
        Tracker = await get_tracker(ctx, engine)
        Condition = await get_condition(ctx, engine)
    else:
        Tracker = await get_tracker(ctx, engine, id=guild.id)
        Condition = await get_condition(ctx, engine, id=guild.id)

    async with async_session() as session:
        result = await session.execute(select(Condition).where(Condition.time == True))
        con_list = result.scalars().all()

    for row in con_list:
        await asyncio.sleep(0)
        time_stamp = datetime.datetime.fromtimestamp(row.number)
        time_left = time_stamp - current_time
        if time_left.total_seconds() <= 0:
            async with async_session() as session:
                result = await session.execute(select(Tracker).where(Tracker.id == row.character_id))
                character = result.scalars().one()
            async  with async_session() as session:
                await session.delete(row)
                await session.commit()
            if ctx != None:
                await ctx.channel.send(f"{row.title} removed from {character.name}")
            else:
                tracker_channel = bot.get_channel(guild.tracker_channel)
                tracker_channel.send(f"{row.title} removed from {character.name}")
    await engine.dispose()


# ---------------------------------------------------------------
# ---------------------------------------------------------------
# UTILITY FUNCTIONS

# Checks to see if the user of the slash command is the GM, returns a boolean
async def gm_check(ctx, engine):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()
            if int(guild.gm) != int(ctx.interaction.user.id):
                return False
            else:
                return True
    except Exception as e:
        return False


# checks to see if the player is the ower of the character
# possibly depreciated due to auto-complete
async def player_check(ctx: discord.ApplicationContext, engine, bot, character: str):
    logging.info(f"{datetime.datetime.now()} - {inspect.stack()[0][3]} - {sys.argv[0]}")
    try:
        Tracker = await get_tracker(ctx, engine)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            char_result = await session.execute(select(Tracker).where(
                Tracker.name == character))
            character = char_result.scalars().one()
        return character

    except Exception as e:
        print(f'player_check: {e}')
        report = ErrorReport(ctx, player_check.__name__, e, bot)
        await report.report()


#############################################################################
#############################################################################
# Specific character modals

class PF2AddCharacterModal(discord.ui.Modal):
    def __init__(self, name: str, hp: int, init: str, initiative, player, ctx, engine, bot, *args, **kwargs):
        self.name = name
        self.hp = hp
        self.init = init
        self.initiative = initiative
        self.player = player
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
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
            ), *args, **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
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

        embed = discord.Embed(
            title="Character Created (PF2)",
            fields=[
                discord.EmbedField(
                    name="Name: ", value=self.name, inline=True
                ),
                discord.EmbedField(
                    name="HP: ", value=f"{self.hp}", inline=True
                ),
                discord.EmbedField(
                    name="AC: ", value=self.children[0].value, inline=True
                ),
                discord.EmbedField(
                    name="Fort: ", value=self.children[1].value, inline=True
                ),
                discord.EmbedField(
                    name="Reflex: ", value=self.children[2].value, inline=True
                ),
                discord.EmbedField(
                    name="Will: ", value=self.children[3].value, inline=True
                ),
                discord.EmbedField(
                    name="Class/Spell DC: ", value=self.children[4].value, inline=True
                ),
                discord.EmbedField(
                    name="Initiative: ", value=self.init, inline=True
                ),
            ],
            color=discord.Color.dark_gold(),
        )

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            Tracker = await get_tracker(self.ctx, self.engine, id=guild.id)
            async with session.begin():
                tracker = Tracker(
                    name=self.name,
                    init_string=self.init,
                    init=self.initiative,
                    player=self.player,
                    user=self.ctx.user.id,
                    current_hp=self.hp,
                    max_hp=self.hp,
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
                number=int(self.children[0].value),
                counter=True,
                visible=False))
            session.add(Condition(
                character_id=character.id,
                title='Fort',
                number=int(self.children[1].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Reflex',
                number=int(self.children[2].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Will',
                number=int(self.children[3].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='DC',
                number=int(self.children[4].value),
                counter=True,
                visible=False
            ))
            await session.commit()

        async with session.begin():
            if guild.initiative != None:
                if not await init_integrity_check(self.ctx, guild.initiative, guild.saved_order, self.engine):
                    # print(f"integrity check was false: init_pos: {guild.initiative}")
                    for pos, row in enumerate(await get_init_list(self.ctx, self.engine)):
                        await asyncio.sleep(0)
                        if row.name == guild.saved_order:
                            guild.initiative = pos
                            # print(f"integrity checked init_pos: {guild.initiative}")
                            await session.commit()

        await update_pinned_tracker(self.ctx, self.engine, self.bot)

        # await update_pinned_tracker(self.ctx, self.engine, self.bot)
        print('Tracker Updated')
        await interaction.response.send_message(embeds=[embed])

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        print(error)


# D&D 4e Specific
class D4eAddCharacterModal(discord.ui.Modal):
    def __init__(self, name: str, hp: int, init: str, initiative, player, ctx, engine, bot, *args, **kwargs):
        self.name = name
        self.hp = hp
        self.init = init
        self.initiative = initiative
        self.player = player
        self.ctx = ctx
        self.engine = engine
        self.bot = bot
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
            ), *args, **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
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

        embed = discord.Embed(
            title="Character Created (D&D 4e)",
            fields=[
                discord.EmbedField(
                    name="Name: ", value=self.name, inline=True
                ),
                discord.EmbedField(
                    name="HP: ", value=f"{self.hp}", inline=True
                ),
                discord.EmbedField(
                    name="AC: ", value=self.children[0].value, inline=True
                ),
                discord.EmbedField(
                    name="Fort: ", value=self.children[1].value, inline=True
                ),
                discord.EmbedField(
                    name="Reflex: ", value=self.children[2].value, inline=True
                ),
                discord.EmbedField(
                    name="Will: ", value=self.children[3].value, inline=True
                ),
                discord.EmbedField(
                    name="Initiative: ", value=self.init, inline=True
                ),
            ],
            color=discord.Color.dark_gold(),
        )

        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            Tracker = await get_tracker(self.ctx, self.engine, id=guild.id)
            async with session.begin():
                tracker = Tracker(
                    name=self.name,
                    init_string=self.init,
                    init=self.initiative,
                    player=self.player,
                    user=self.ctx.user.id,
                    current_hp=self.hp,
                    max_hp=self.hp,
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
                number=int(self.children[0].value),
                counter=True,
                visible=False))
            session.add(Condition(
                character_id=character.id,
                title='Fort',
                number=int(self.children[1].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Reflex',
                number=int(self.children[2].value),
                counter=True,
                visible=False
            ))
            session.add(Condition(
                character_id=character.id,
                title='Will',
                number=int(self.children[3].value),
                counter=True,
                visible=False
            ))
            await session.commit()

        async with session.begin():
            if guild.initiative != None:
                if not await init_integrity_check(self.ctx, guild.initiative, guild.saved_order, self.engine):
                    # print(f"integrity check was false: init_pos: {guild.initiative}")
                    for pos, row in enumerate(await get_init_list(self.ctx, self.engine)):
                        await asyncio.sleep(0)
                        if row.name == guild.saved_order:
                            guild.initiative = pos
                            # print(f"integrity checked init_pos: {guild.initiative}")
                            await session.commit()

        await update_pinned_tracker(self.ctx, self.engine, self.bot)
        print('Tracker Updated')
        await interaction.response.send_message(embeds=[embed])

    async def on_error(self, error: Exception, interaction: Interaction) -> None:
        print(error)


#############################################################################
#############################################################################
# SLASH COMMANDS
# The Initiative Cog
class InitiativeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.update_status.start()
        # self.check_latency.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    # @tasks.loop(seconds=30)
    # async def check_latency(self):
    #     logging.info(f"{self.bot.latency}: {datetime.datetime.now()}")

    # Update the bot's status periodically
    @tasks.loop(minutes=1)
    async def update_status(self):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            guild = await session.execute(select(Global))
            result = guild.scalars().all()
            count = len(result)
        async with self.lock:
            await self.bot.change_presence(activity=discord.Game(name=f"ttRPGs in {count} tables across the "
                                                                      f"digital universe."))

    # Don't start the loop unti the bot is ready
    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()

    async def time_check_ac(self, ctx: discord.AutocompleteContext):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        if await check_timekeeper(ctx, engine):
            return ['Round', 'Minute', 'Hour', 'Day']
        else:
            return ['Round']

    # ---------------------------------------------------
    # ---------------------------------------------------
    # Slash commands

    i = SlashCommandGroup("i", "Initiative Tracker")
    char = SlashCommandGroup("char", "Character Commands")
    cc = SlashCommandGroup("cc", "Conditions and Counters")

    @char.command(description="Add PC on NPC",
                  # guild_ids=[GUILD]
                  )
    @option('name', description="Character Name", input_type=str)
    @option('hp', description='Total HP', input_type=int)
    @option('player', choices=['player', 'npc'], input_type=str)
    @option('initiative', description="Initiative Roll (XdY+Z)", required=True, input_type=str)
    async def add(self, ctx: discord.ApplicationContext, name: str, hp: int,
                  player: str, initiative: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        # await ctx.response.defer(ephemeral=True)
        response = False
        player_bool = False
        if player == 'player':
            player_bool = True
        elif player == 'npc':
            player_bool = False

        response = await add_character(ctx, engine, self.bot, name, hp, player_bool, initiative)
        if response:
            await ctx.respond(f"Character {name} added successfully.", ephemeral=True)
        else:
            await ctx.respond(f"Error Adding Character", ephemeral=True)

    @char.command(description="Edit PC on NPC")
    @option('name', description="Character Name", input_type=str, autocomplete=character_select_gm, )
    @option('hp', description='Total HP', input_type=int, required=False)
    @option('initiative', description="Initiative Roll (XdY+Z)", required=False, input_type=str)
    @option('active', description='Active State', required=False, input_type=bool)
    async def edit(self, ctx: discord.ApplicationContext, name: str, hp: int = None, initiative: str = None, active:bool=None,
                   player: discord.User = None):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        if await auto_complete.hard_lock(ctx, name):
            response = await edit_character(ctx, engine, self.bot, name, hp, initiative, active, player)
            if not response:
                await ctx.respond(f"Error Editing Character", ephemeral=True)

            await update_pinned_tracker(ctx, engine, self.bot)
        else:
            await ctx.respond("You do not have the appropriate permissions to edit this character.")

    @char.command(description="Duplicate Character")
    @option('name', description="Character Name", input_type=str, autocomplete=character_select_gm, )
    @option('new_name', description='Name for the new NPC', input_type=str, required=True)
    async def copy(self, ctx: discord.ApplicationContext, name: str, new_name: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer(ephemeral=True)
        response = False
        response = await copy_character(ctx, engine, self.bot, name, new_name)
        if response:
            await ctx.send_followup(f"{new_name} Created", ephemeral=True)
        else:
            await ctx.send_followup(f"Error Copying Character", ephemeral=True)

        await update_pinned_tracker(ctx, engine, self.bot)

    @char.command(description="Delete NPC")
    @option('name', description="Character Name", input_type=str, autocomplete=npc_select, )
    async def delete(self, ctx: discord.ApplicationContext, name: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        await ctx.response.defer(ephemeral=True)
        if await auto_complete.hard_lock(ctx, name):
            try:
                async with async_session() as session:
                    result = await session.execute(select(Global).where(
                        or_(
                            Global.tracker_channel == ctx.interaction.channel_id,
                            Global.gm_tracker_channel == ctx.interaction.channel_id
                        )
                    )
                    )
                    guild = result.scalars().one()

                if name == guild.saved_order:
                    await ctx.send_followup(
                        f"Please wait until {name} is not the active character in initiative before "
                        f"deleting it.", ephemeral=True)
                else:
                    result = await delete_character(ctx, name, engine, self.bot)
                    if result:
                        await ctx.send_followup(f'{name} deleted', ephemeral=True)
                        await update_pinned_tracker(ctx, engine, self.bot)
                    else:
                        await ctx.send_followup('Delete Operation Failed', ephemeral=True)
                await engine.dispose()
            except NoResultFound as e:
                await ctx.respond(
                    error_not_initialized,
                    ephemeral=True)
                return False
            except IndexError as e:
                await ctx.respond("Ensure that you have added characters to the initiative list.")
            except Exception as e:
                await ctx.respond("Failed")
        else:
            await ctx.respond("You do not have the appropriate permissions to delete this character.")

    @char.command(description="Display Character Sheet")
    @option('name', description="Character Name", input_type=str, autocomplete=character_select_gm, )
    async def sheet(self, ctx: discord.ApplicationContext, name: str):
        await ctx.response.defer(ephemeral=True)
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        if await auto_complete.hard_lock(ctx, name):
            embed = await get_char_sheet(ctx, engine, self.bot, name)
            await ctx.send_followup(embeds=embed)
        else:
            ctx.send_followup("You do not have the appropriate permissions to view this character.")

    @i.command(description="Manage Initiative",
               # guild_ids=[GUILD]
               )
    @discord.default_permissions(manage_messages=True)
    @option('mode', choices=['start', 'stop', 'delete character'], required=True)
    @option('character', description='Character to delete', required=False)
    async def manage(self, ctx: discord.ApplicationContext, mode: str, character: str = ''):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with async_session() as session:
                result = await session.execute(select(Global).where(
                    or_(
                        Global.tracker_channel == ctx.interaction.channel_id,
                        Global.gm_tracker_channel == ctx.interaction.channel_id
                    )
                )
                )
                guild = result.scalars().one()
            if not await gm_check(ctx, engine):
                await ctx.respond("GM Restricted Command", ephemeral=True)
                return
            else:
                if mode == 'start':
                    await ctx.response.defer()
                    await block_advance_initiative(ctx, engine, self.bot)
                    await block_post_init(ctx, engine, self.bot)
                    # await update_pinned_tracker(ctx, engine, self.bot)
                    # await ctx.respond('Initiative Started', ephemeral=True)
                elif mode == 'stop':  # Stop initiative
                    await ctx.response.defer()
                    # remove the buttons from the last tracker
                    try:
                        tracker_channel = self.bot.get_channel(guild.tracker_channel)
                        old_tracker_msg = await tracker_channel.fetch_message(guild.last_tracker)
                        await old_tracker_msg.edit(view=None)
                    except Exception as e:
                        pass

                    # Reset variables to the neutral state
                    async with async_session() as session:
                        result = await session.execute(select(Global).where(
                            or_(
                                Global.tracker_channel == ctx.interaction.channel_id,
                                Global.gm_tracker_channel == ctx.interaction.channel_id
                            )
                        )
                        )
                        guild = result.scalars().one()
                        guild.initiative = None
                        guild.saved_order = ''
                        guild.round = 0
                        guild.last_tracker = None
                        await session.commit()
                    metadata = db.MetaData()
                    # Update the tables
                    Tracker = await get_tracker(ctx, engine, id=guild.id)
                    Condition = await get_condition(ctx, engine, id=guild.id)

                    # tracker cleanup
                    # Delete condition with round timers
                    async  with async_session() as session:
                        result = await session.execute(
                            select(Condition).where(Condition.auto_increment == True).where(Condition.time == False))
                        con_del_list = result.scalars().all()
                    for con in con_del_list:
                        await asyncio.sleep(0)
                        print(con.title)
                        async with async_session() as session:
                            await session.delete(con)
                            await session.commit()

                    # Delete any dead NPCs
                    async with async_session() as session:
                        result = await session.execute(
                            select(Tracker).where(Tracker.current_hp <= 0).where(Tracker.player == False))
                        delete_list = result.scalars().all()
                    for npc in delete_list:
                        await delete_character(ctx, npc.name, engine, self.bot)

                    # Set all initiatives to 0
                    async with async_session() as session:
                        result = await session.execute(select(Tracker))
                        tracker_list = result.scalars().all()
                        for item in tracker_list:
                            item.init = 0
                        await session.commit()
                    await update_pinned_tracker(ctx, engine, self.bot)
                    await ctx.send_followup("Initiative Ended.")
                elif mode == 'delete character':
                    print(f'Character {character}')
                    print(f'Saved: {guild.saved_order}')
                    if character == guild.saved_order:
                        await ctx.respond(
                            f"Please wait until {character} is not the active character in initiative before "
                            f"deleting it.", ephemeral=True)
                    else:
                        await ctx.response.defer(ephemeral=True)
                        result = await delete_character(ctx, character, engine, self.bot)
                        if result:
                            await ctx.send_followup(f'{character} deleted', ephemeral=True)
                            await update_pinned_tracker(ctx, engine, self.bot)
                        else:
                            await ctx.send_followup('Delete Operation Failed', ephemeral=True)
            await engine.dispose()
        except NoResultFound as e:
            await ctx.respond(
                error_not_initialized,
                ephemeral=True)
            return False
        except IndexError as e:
            await ctx.respond("Ensure that you have added characters to the initiative list.")
        except Exception as e:
            await ctx.respond("Failed")

    @i.command(description="Advance Initiative",
               # guild_ids=[GUILD]
               )
    async def next(self, ctx: discord.ApplicationContext):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        try:
            await ctx.response.defer()
            # Advance Init and Display
            await block_advance_initiative(ctx, engine, self.bot)  # Advance the init

            # Query the initiative position for the tracker and post it
            await block_post_init(ctx, engine, self.bot)
            # await update_pinned_tracker(ctx, engine, self.bot)  # update the pinned tracker

        except NoResultFound as e:
            await ctx.respond(error_not_initialized, ephemeral=True)
        except PermissionError as e:
            await ctx.message.delete()
        except Exception as e:
            await ctx.respond('Error', ephemeral=True)
            print(f"/i next: {e}")
            report = ErrorReport(ctx, "slash command /i next", e, self.bot)
            await report.report()

    @i.command(description="Set Init (Number or XdY+Z)",
               # guild_ids=[GUILD]
               )
    @option("character", description="Character to select", autocomplete=character_select_gm, )
    async def init(self, ctx: discord.ApplicationContext, character: str, init: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:
            result = await session.execute(select(Global).where(
                or_(
                    Global.tracker_channel == ctx.interaction.channel_id,
                    Global.gm_tracker_channel == ctx.interaction.channel_id
                )
            )
            )
            guild = result.scalars().one()

            if character == guild.saved_order:
                await ctx.respond(f"Please wait until {character} is not the active character in initiative before "
                                  f"resetting its initiative.", ephemeral=True)
            else:
                dice = DiceRoller('')
                try:
                    # print(f"Init: {init}")
                    initiative = int(init)
                    success = await set_init(ctx, self.bot, character, initiative, engine)
                    if success:
                        await ctx.respond(f"Initiative set to {initiative} for {character}")
                    else:
                        await ctx.respond("Failed to set initiative.", ephemeral=True)
                except:
                    roll = await dice.plain_roll(init)
                    success = await set_init(ctx, self.bot, character, roll[1], engine)
                    if success:
                        await ctx.respond(f"Initiative set to {roll[0]} = {roll[1]} for {character}")
                    else:
                        await ctx.respond("Failed to set initiative.", ephemeral=True)
            await update_pinned_tracker(ctx, engine, self.bot)
        await engine.dispose()

    @i.command(description="Heal, Damage or add Temp HP",
               # guild_ids=[GUILD]
               )
    @option('name', description="Character Name", autocomplete=character_select)
    @option('mode', choices=['Damage', 'Heal', "Temporary HP"])
    async def hp(self, ctx: discord.ApplicationContext, name: str, mode: str, amount: int):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        response = False
        await ctx.response.defer()
        if mode == 'Heal':
            response = await change_hp(ctx, engine, self.bot, name, amount, True)
        elif mode == 'Damage':
            response = await change_hp(ctx, engine, self.bot, name, amount, False)
        elif mode == 'Temporary HP':
            response = await add_thp(ctx, engine, self.bot, name, amount)
            if response:
                await ctx.respond(f"{amount} Temporary HP added to {name}.")
        if not response:
            await ctx.respond("Failed", ephemeral=True)
        await update_pinned_tracker(ctx, engine, self.bot)

    @cc.command(description="Add conditions and counters",
                # guild_ids=[GUILD]
                )
    @option("character", description="Character to select", autocomplete=character_select)
    @option('type', choices=['Condition', 'Counter'])
    @option('auto', description="Auto Decrement", choices=['Auto Decrement', 'Static'])
    @option('unit', autocomplete=time_check_ac)
    @option('flex', autocomplete=discord.utils.basic_autocomplete(["True", "False"]))
    async def new(self, ctx: discord.ApplicationContext, character: str, title: str, type: str, number: int = None,
                  unit: str = "Round",
                  auto: str = 'Static',
                  flex: str = "False"):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        await ctx.response.defer()
        if flex == 'False':
            flex_bool = False
        else:
            flex_bool = True

        if type == "Condition":
            counter_bool = False
        else:
            counter_bool = True
        if auto == 'Auto Decrement':
            auto_bool = True
        else:
            auto_bool = False

        response = await set_cc(ctx, engine, character, title, counter_bool, number, unit, auto_bool, self.bot,
                                flex=flex_bool)
        if response:
            await ctx.send_followup(f"Condition {title} added on {character}")
        else:
            await ctx.send_followup("Add Condition/Counter Failed")

    @cc.command(description="Edit or remove conditions and counters",
                # guild_ids=[GUILD]
                )
    @option('mode', choices=['edit', 'delete'])
    @option("character", description="Character to select", autocomplete=character_select)
    @option("condition", description="Condition", autocomplete=cc_select)
    async def edit(self, ctx: discord.ApplicationContext, mode: str, character: str, condition: str):
        engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
        result = False
        await ctx.response.defer(ephemeral=True)
        if mode == 'delete':
            result = await delete_cc(ctx, engine, character, condition, self.bot)
            if result:
                await ctx.send_followup('Successful Delete', ephemeral=True)
                await ctx.send(f"{condition} on {character} deleted.")
        elif mode == 'edit':
            output = await edit_cc_interface(ctx, engine, character, condition, self.bot)
            if output[0] != None:
                await ctx.send_followup(output[0], view=output[1], ephemeral=True)
            else:
                await ctx.send_followup('Error')
            # result = await edit_cc(ctx, engine, character, condition, new_value, self.bot)
            # if result:
            #     await ctx.send_followup(f"{condition} on {character} updated.")
        else:
            await ctx.send_followup("Invalid Input", ephemeral=True)

    # @cc.command(description="Show Custom Counters")
    # @option("character", description="Character to select", autocomplete=character_select_gm)
    # async def show(self, ctx: discord.ApplicationContext, character: str):
    #     engine = get_asyncio_db_engine(user=USERNAME, password=PASSWORD, host=HOSTNAME, port=PORT, db=SERVER_DATA)
    #     await ctx.response.defer(ephemeral=True)
    #     try:
    #         if not await auto_complete.hard_lock(ctx, character):
    #             await ctx.send_followup(f'Viewing NPC counters is restricted to the GM only.', ephemeral=True)
    #         else:
    #             cc_list = await get_cc(ctx, engine, self.bot, character)
    #             output_string = f'```{character}:\n'
    #             for row in cc_list:
    #                 await asyncio.sleep(0)
    #                 counter_string = f'{row.title}: {row.number}'
    #                 output_string += counter_string
    #                 output_string += '\n'
    #             output_string += "```"
    #             await ctx.send_followup(output_string, ephemeral=True)
    #     except Exception as e:
    #         print(f'cc_show: {e}')
    #         await ctx.send_followup(f'Failed: Ensure that {character} is a valid character', ephemeral=True)


def setup(bot):
    bot.add_cog(InitiativeCog(bot))
