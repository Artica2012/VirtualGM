# imports
import asyncio
import logging
from datetime import datetime

import discord
from sqlalchemy import select, true, or_, false
from sqlalchemy.exc import NoResultFound

from Backend.Database.database_models import get_tracker, Global, get_condition, get_macro
from Backend.WS.WebsocketHandler import socket
from Backend.utils.error_handling_reporting import ErrorReport, error_not_initialized
from Backend.utils.time_keeping_functions import advance_time, output_datetime, get_time
from Backend.utils.Char_Getter import get_character
from Backend.utils.utils import get_guild
from Backend.Database.engine import async_session
import Backend.Database.engine


async def get_init_list(ctx: discord.ApplicationContext, engine, guild=None):
    """
    Returns the list of characters in initiative, in descending order
    :param ctx:
    :param engine:
    :param guild:
    :return: init_list (list of Tracker Objects)
    """

    logging.info("get_init_list")
    try:
        if guild is not None:
            try:
                Tracker = await get_tracker(ctx, id=guild.id)
            except Exception:
                Tracker = await get_tracker(ctx)
        else:
            Tracker = await get_tracker(ctx)

        async with async_session() as session:
            result = await session.execute(
                select(Tracker)
                .where(Tracker.active == true())
                .order_by(Tracker.init.desc())
                .order_by(Tracker.id.desc())
            )
            init_list = result.scalars().all()
            logging.info("GIL: Init list gotten")
            # print(init_list)
        return init_list

    except Exception:
        logging.error("error in get_init_list")
        return []


class Tracker:
    def __init__(self, ctx, engine, init_list, bot, guild=None):
        """
        The Tracker Class. Contains the methods for manipulating and advancing initiative.

        :param ctx:
        :param engine:
        :param init_list: (output of function get_init_list)
        :param bot:
        :param guild:
        """

        self.ctx = ctx
        self.engine = Backend.Database.engine.engine
        self.init_list = init_list
        self.guild = guild
        self.bot = bot

    async def next(self):
        """
        Advances the turn and updates the tracker.

        :return: No return value
        """

        await self.advance_initiative()
        await self.block_post_init()

    async def block_next(self, interaction: discord.Interaction, id=None):
        """
        Intelligent next command for the next button on the block tracker. Should only be by a button.

        :param interaction: (discord.Interaction from a button press)
        :return: No return value
        """
        success = False

        if id is None:
            id = interaction.user.id

        advance = True
        if self.guild.block:
            advance = False
            if id in self.guild.block_data:
                # If the player has not yet pressed the button this block, and they are in the block list, then remove
                # their name from the list of players that still need to go.
                new_block = self.guild.block_data.copy()
                new_block.remove(id)

                async with async_session() as session:
                    result = await session.execute(select(Global).where(Global.id == self.guild.id))
                    guild = result.scalars().one()
                    guild.block_data = new_block  # Update the block list in the database.
                    await session.commit()
                await self.update()
                if len(new_block) == 0:
                    advance = True  # If the block list is now empty, advance the turn
                else:
                    if interaction is not None:
                        await interaction.response.send_message(
                            (
                                "Turn Marked Complete. Initiative Will Advance once all players have marked"
                                " themselves complete"
                            ),
                            ephemeral=True,
                        )
                    await self.block_post_init()
                if id == int(self.guild.gm):
                    # If the player is the gm, automatically advance the turn even if the block list isn't empty
                    advance = True
                success = True
            else:
                advance = False
                if interaction is not None:
                    await interaction.response.send_message(
                        "Either it is not your turn, or you have already marked yourself complete", ephemeral=True
                    )
        if advance:
            if interaction is not None:
                await interaction.response.send_message("Initiative Advanced", ephemeral=True)
            await self.next()

        return success

    async def reroll_init(self):
        """
        Convenience method that seamlessly ends initiative and restarts it without cleaning up, to effectively reroll
        initiative.

        :return: No return value
        """

        await self.end(clean=False)
        await self.update()
        await self.next()

    async def get_init_list(self, ctx: discord.ApplicationContext, engine, guild=None):
        """
        This is a copy of the get_init_list function as a class method. This is here to allow overrides of the
        initiative order in subclasses.  The default is unchanged from the function.

        :param ctx:
        :param engine:
        :param guild:
        :return: init_list (list of tracker objects) - Returns an empty list on error.
        """

        logging.info("get_init_list")
        try:
            if guild is not None:
                try:
                    Tracker = await get_tracker(ctx, id=guild.id)
                except Exception:
                    Tracker = await get_tracker(ctx)
            else:
                Tracker = await get_tracker(ctx)

            async with async_session() as session:
                result = await session.execute(
                    select(Tracker)
                    .where(Tracker.active == true())
                    .order_by(Tracker.init.desc())
                    .order_by(Tracker.id.desc())
                )
                init_list = result.scalars().all()
                logging.info("GIL: Init list gotten")
            return init_list

        except Exception:
            logging.error("error in get_init_list")
            return []

    async def get_char_from_id(self, char_id: int):
        """
        Returns a character model from the reference id. This is used primarily (at the moment) to get the character
         model for conditions that decrement on another character's turn.

        :param char_id: (Integer)
        :return: Character Model (Character Class) or appropriate subclass
        """

        Char_Tracker = await get_tracker(self.ctx, id=self.guild.id)
        async with async_session() as session:
            result = await session.execute(select(Char_Tracker).where(Char_Tracker.id == char_id))
        character = result.scalars().one()
        return await get_character(character.name, self.ctx, guild=self.guild)

    async def end(self, clean=True):
        """
        Method that ends initiative. Resets variables to their neutral state. If clean = True, it will delete conditions
        that are round based on time, and delete all NPCs with 0 or less HP.

        :param clean: bool (Default = True)
        :return: No return value
        """

        try:
            tracker_channel = self.bot.get_channel(self.guild.tracker_channel)
            old_tracker_msg = await tracker_channel.fetch_message(self.guild.last_tracker)
            await old_tracker_msg.edit(view=None)
        except Exception:
            pass

        # Reset variables to the neutral state
        async with async_session() as session:
            result = await session.execute(select(Global).where(Global.id == self.guild.id))
            guild = result.scalars().one()
            guild.initiative = None
            guild.saved_order = ""
            guild.round = 0
            guild.last_tracker = None
            await session.commit()
        await self.update()
        # Update the tables
        Tracker = await get_tracker(self.ctx, id=self.guild.id)
        Condition = await get_condition(self.ctx, id=self.guild.id)

        # tracker cleanup
        # Delete condition with round timers
        if clean:
            async with async_session() as session:
                result = await session.execute(
                    select(Condition).where(Condition.auto_increment == true()).where(Condition.time == false())
                )
                con_del_list = result.scalars().all()
            for con in con_del_list:
                await asyncio.sleep(0)
                # print(con.title)
                async with async_session() as session:
                    await session.delete(con)
                    await session.commit()

            # Delete any dead NPCs
            async with async_session() as session:
                result = await session.execute(
                    select(Tracker).where(Tracker.current_hp <= 0).where(Tracker.player == false())
                )
                delete_list = result.scalars().all()
            Macro = await get_macro(self.ctx, id=self.guild.id)
            for npc in delete_list:
                async with async_session() as session:
                    # print(character)
                    result = await session.execute(select(Tracker).where(Tracker.name == npc.name))
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
                try:
                    await self.ctx.channel.send(f"{char.name} Deleted")
                except AttributeError:
                    await self.bot.get_channel(int(guild.tracker_channel)).send(f"{char.name} Deleted")

        # Set all initiatives to 0
        async with async_session() as session:
            result = await session.execute(select(Tracker))
            tracker_list = result.scalars().all()
            for item in tracker_list:
                item.init = 0
            await session.commit()
        await self.update()
        await self.update_pinned_tracker()

    async def update(self):
        """
        Method which updates the tracker object with updated initiative list. Needs to be called after changes to
         initiative position, order or adding or removing characters.

        :return: No return value
        """

        self.guild = await get_guild(self.ctx, self.guild, refresh=True)
        self.init_list = await self.get_init_list(self.ctx, self.engine, guild=self.guild)

    async def init_integrity_check(self, init_pos: int, current_character: str):
        """
        Method which check to see if the initiative position is correct. Compares the initiative position in the
        database to the name of the current character in the database to ensure the initiative order has not changed.
        :param: init_pos (integer)
        :param: current_character (string)
        :return: Bool: True if initiative is correct, and false if it is incorrect.
        """

        logging.info("init_integrity_check")
        try:
            if self.init_list[init_pos].name == current_character:
                return True
            else:
                return False
        except IndexError:
            return False
        except Exception as e:
            logging.error(f"init_integrity_check: {e}")
            return False

    async def init_integrity(self):
        """
        Checks for initiative integrity (via the init_itegrity_check method). If it is not correct, it searches for the
        proper position in the initiative list and updates the position accordingly.
        :return: No return value
        """

        logging.info("Checking Initiative Integrity")
        async with async_session() as session:  # Pull the most updated data for the initiative
            result = await session.execute(select(Global).where(Global.id == self.guild.id))
            guild = result.scalars().one()

            if guild.initiative is not None:
                if not await self.init_integrity_check(guild.initiative, guild.saved_order):
                    logging.info("Integrity Check Failed")
                    logging.info(f"Integrity Info: Saved_Order {guild.saved_order}, Init Pos={guild.initiative}")
                    for pos, row in enumerate(self.init_list):  # Iterate through the list to find the correct position
                        if row.name == guild.saved_order:
                            logging.info(f"name: {row.name}, saved_order: {guild.saved_order}")
                            guild.initiative = pos  # update the initiative number in the db to the correct position
                            logging.info(f"Pos: {pos}")
                            logging.info(f"New Init_pos: {guild.initiative}")
                            break  # once its fixed, stop the loop because its done
            await session.commit()

    async def advance_initiative(self):
        """
        This is a switcher function. In the base class it simply calls the block_advance_initiative method. In
        subclasses it may call different methods depending on particular parameters. This is for future-proofing.

        :return:boolean output of the  block_advance_initiative method.
        """

        return await self.block_advance_initiative()

    async def block_advance_initiative(self):
        """
        Advances initiative. This is an internal method and should be called by via the advance_initiative method.
        This particular method takes block initiative into account.

        :return:Boolean: True for success and false for failure
        """
        logging.info("advance_initiative")

        block_done = False
        turn_list = []
        first_pass = False
        round = self.guild.round

        try:
            logging.info(f"BAI1: guild: {self.guild.id}")

            Tracker = await get_tracker(self.ctx, id=self.guild.id)
            async with async_session() as session:
                char_result = await session.execute(select(Tracker))
                character = char_result.scalars().all()
                logging.info("BAI2: characters")

                # Roll initiative if this is the start of init
                # print(f"guild.initiative: {guild.initiative}")
                if self.guild.initiative is None:
                    init_pos = -1
                    round = 1
                    first_pass = True
                    for char in character:
                        await asyncio.sleep(0)
                        model = await get_character(char.name, self.ctx, guild=self.guild)
                        if model.init == 0:
                            await asyncio.sleep(0)
                            try:
                                # roll = d20.roll(char.init_string)
                                await model.roll_initiative()
                            except Exception:
                                await model.set_init(0)
                else:
                    init_pos = int(self.guild.initiative)

            await self.update()
            logging.info("BAI3: updated")

            if self.guild.saved_order == "":
                current_character = await get_character(self.init_list[0].name, self.ctx, guild=self.guild)
            else:
                current_character = await get_character(self.guild.saved_order, self.ctx, guild=self.guild)

            # Record the initial to break an infinite loop
            iterations = 0
            logging.info(f"BAI4: iteration: {iterations}")

            while not block_done:
                # make sure that the current character is at the same place in initiative as it was before
                # decrement any conditions with the decrement flag

                if self.guild.block:  # if in block initiative, decrement conditions at the beginning of the turn
                    # if its not, set the init position to the position of the current character before advancing it
                    # print("Yes guild.block")
                    logging.info(f"BAI5: guild.block: {self.guild.block}")
                    if not await self.init_integrity_check(init_pos, current_character.char_name) and not first_pass:
                        logging.info("BAI6: init_itegrity failied")
                        for pos, row in enumerate(self.init_list):
                            await asyncio.sleep(0)
                            if row.name == current_character.char_name:
                                init_pos = pos
                                break
                    init_pos += 1  # increase the init position by 1

                    if init_pos >= len(self.init_list):  # if it has reached the end, loop back to the beginning
                        init_pos = 0
                        round += 1
                        if self.guild.timekeeping:  # if timekeeping is enable on the server
                            logging.info("BAI7: timekeeping")
                            # Advance time time by the number of seconds in the guild.time column. Default is 6
                            # seconds ala D&D standard
                            await advance_time(self.ctx, self.engine, None, second=self.guild.time, guild=self.guild)
                            await current_character.check_time_cc()
                            logging.info("BAI8: cc checked")

                # Decrement the conditions
                await self.init_con(current_character, None)

                if not self.guild.block:  # if not in block initiative, decrement the conditions at the end of the turn
                    logging.info("BAI14: Not Block")
                    # print("Not guild.block")
                    # if its not, set the init position to the position of the current character before advancing it
                    if not await self.init_integrity_check(init_pos, current_character.char_name) and not first_pass:
                        logging.info("BAI15: Integrity check failed")
                        # print(f"integrity check was false: init_pos: {init_pos}")
                        for pos, row in enumerate(self.init_list):
                            await asyncio.sleep(0)
                            if row.name == current_character.char_name:
                                init_pos = pos

                    init_pos += 1  # increase the init position by 1
                    if init_pos >= len(self.init_list):  # if it has reached the end, loop back to the beginning
                        init_pos = 0
                        round += 1
                        if self.guild.timekeeping:  # if timekeeping is enable on the server
                            # Advance time time by the number of seconds in the guild.time column. Default is 6
                            # seconds ala D&D standard
                            await advance_time(self.ctx, self.engine, None, second=self.guild.time, guild=self.guild)
                            # await current_character.check_time_cc(self.bot)
                            logging.info("BAI16: cc checked")

                            # block initiative loop
                # check to see if the next character is player vs npc

                if init_pos >= len(self.init_list) - 1:
                    # print(f"init_pos: {init_pos}")
                    if self.init_list[init_pos].player != self.init_list[0].player:
                        block_done = True
                elif self.init_list[init_pos].player != self.init_list[init_pos + 1].player:
                    block_done = True
                if not self.guild.block:
                    block_done = True

                # turn_list.append(self.init_list[init_pos].name)
                if self.init_list[init_pos].user not in turn_list:
                    turn_list.append(self.init_list[init_pos].user)

                current_character = await get_character(self.init_list[init_pos].name, self.ctx, guild=self.guild)
                iterations += 1
                if iterations >= len(self.init_list):  # stop an infinite loop
                    block_done = True

                # print(turn_list)

            async with async_session() as session:
                if self.ctx is None:
                    result = await session.execute(select(Global).where(Global.id == self.guild.id))
                else:
                    result = await session.execute(
                        select(Global).where(
                            or_(
                                Global.tracker_channel == self.ctx.interaction.channel_id,
                                Global.gm_tracker_channel == self.ctx.interaction.channel_id,
                            )
                        )
                    )
                guild = result.scalars().one()
                logging.info(f"BAI17: guild updated: {guild.id}")
                guild.initiative = init_pos  # set it
                guild.round = round
                guild.saved_order = str(self.init_list[init_pos].name)
                guild.block_data = turn_list
                logging.info(f"BAI18: saved order: {guild.saved_order}")
                await session.commit()
                logging.info("BAI19: Written")
            await self.update()
            return True
        except Exception as e:
            logging.error(f"block_advance_initiative: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "block_advance_initiative", e, self.bot)
                await report.report()

    # This is the code which check, decrements and removes conditions for the init next turn.
    async def init_con(self, current_character, before: bool):
        """
        This method checks conditions as initiative advances and decrements or removes them as appropriate. Internal
        method that should be called during the initiative advancement.

        :param current_character: (character model of the Character class)
        :param before: (bool - This determines if its being called at the beginning or ending of the turn, to allow for
            conditions that decrement at a specific portion. Pass None to decrement all appropriate conditions or for
            subclasses (systems) that don't differentiate eg D&D 4e.
        :return: No return value
        """

        logging.info(f"{current_character.char_name}, {before}")
        logging.info("Decrementing Conditions")

        # Run through the conditions on the current character

        try:
            Condition = await get_condition(self.ctx, id=self.guild.id)
            async with async_session() as session:
                if before is not None:
                    char_result = await session.execute(
                        select(Condition)
                        .where(Condition.target == current_character.id)
                        .where(Condition.flex == before)
                        .where(Condition.auto_increment == true())
                    )
                else:
                    char_result = await session.execute(
                        select(Condition)
                        .where(Condition.target == current_character.id)
                        .where(Condition.auto_increment == true())
                    )
                con_list = char_result.scalars().all()
                # print(len(con_list))
                logging.info("BAI9: condition's retrieved")
                # print("First Con List")

            for con_row in con_list:
                # print(con_row.title)
                Con_Character = await self.get_char_from_id(con_row.character_id)
                # print(Con_Character.char_name)
                logging.info(f"BAI10: con_row: {con_row.title} {con_row.id}")
                await asyncio.sleep(0)
                if not con_row.time:
                    if con_row.number >= 2:
                        await Con_Character.edit_cc(con_row.title, con_row.number - 1)
                    else:
                        await Con_Character.delete_cc(con_row.title)
                        del_embed = discord.Embed(
                            title=Con_Character.char_name,
                            description=f"{con_row.title} removed from {Con_Character.char_name}",
                        )
                        del_embed.set_thumbnail(url=Con_Character.pic)
                        if self.ctx is not None:
                            await self.ctx.channel.send(embed=del_embed)
                        elif self.bot is not None:
                            tracker_channel = self.bot.get_channel(self.guild.tracker_channel)
                            await tracker_channel.send(embed=del_embed)
                else:
                    await Con_Character.check_time_cc()

        except Exception as e:
            logging.error(f"block_advance_initiative: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "init_con", e, self.bot)
                await report.report()

    async def get_inactive_list(self):
        """
        Method which pulls the list of inactive characters from the database and returns it.

        :return: list of character models
        """

        logging.info("get_inactive_list")
        Tracker = await get_tracker(self.ctx, id=self.guild.id)
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Tracker)
                    .where(Tracker.active == false())
                    .order_by(Tracker.init.desc())
                    .order_by(Tracker.id.desc())
                )
                init_list = result.scalars().all()
                logging.info("GIL: Init list gotten")
                # print(init_list)
            return init_list
        except Exception:
            logging.error("error in get_init_list")
            return []

    async def block_get_tracker(self, selected: int, gm: bool = False):  # Probably should rename this eventually
        """
        This method formats the tracker as a complex string. This is the base tracker, with each subclass having a
        version specific to that RPG system.
        :param selected: (integer id of the current character)
        :param gm: bool True for GM tracker, false for player tracker
        :return: output string
        """
        logging.info("generic_block_get_tracker")
        logging.error(
            "depreciation warning. This method has been depreciated. If you are seeing this, then you missed updating"
            " to the new version"
        )
        # Get the datetime
        datetime_string = ""

        # Get the turn List for Block Initiative. If its in block we need the whole turn list and not just
        if self.guild.block and self.guild.initiative is not None:
            turn_list = await self.get_turn_list()
            block = True
        else:
            block = False
        logging.info(f"BGT2: round: {self.guild.round}")

        # Code for appending the inactive list onto the init_list
        total_list = await self.get_init_list(self.ctx, self.engine, guild=self.guild)
        active_length = len(total_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await self.get_inactive_list()
        if len(inactive_list) > 0:
            total_list.extend(inactive_list)
            # print(f'Total Length: {len(init_list)}')

        # Generate the data_time string if timekeeper is active
        try:
            if self.guild.timekeeping:
                datetime_string = (
                    f" {await output_datetime(self.ctx, self.engine, self.bot, guild=self.guild)}"
                    "\n________________________\n"
                )
        except NoResultFound:
            if self.ctx is not None:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
            logging.info("Channel Not Set Up")
        except Exception as e:
            logging.error(f"get_tracker: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "get_tracker", e, self.bot)
                await report.report()

        try:
            Condition = await get_condition(self.ctx, id=self.guild.id)

            # if round = 0, were not in initiative, and act accordingly
            if self.guild.round != 0:
                round_string = f"Round: {self.guild.round}"
            else:
                round_string = ""

            output_string = f"```{datetime_string}Initiative: {round_string}\n"
            # Iterate through the init list
            for x, row in enumerate(total_list):
                character = await get_character(row.name, self.ctx, guild=self.guild)
                logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
                # If there is an inactive list, and this is at the transition, place the line marker
                if len(total_list) > active_length and x == active_length:
                    output_string += "-----------------\n"  # Put in the divider

                # Get all of the visible condition for the character
                async with async_session() as session:
                    result = await session.execute(
                        select(Condition)
                        .where(Condition.character_id == character.id)
                        .where(Condition.visible == true())
                    )
                    condition_list = result.scalars().all()

                await asyncio.sleep(0)  # ensure the loop doesn't lock the bot in case of an error
                sel_bool = False
                selector = "  "

                # don't show an init if not in combat
                if character.init == 0 or character.active is False:
                    init_num = ""
                else:
                    if character.init <= 9:
                        init_num = f" {character.init}"
                    else:
                        init_num = f"{character.init}"

                if block:
                    for (
                        char
                    ) in (
                        turn_list
                    ):  # ignore this error, turn list is gotten if block is true, so this will always apply
                        # print(f'character.id = {character.id}')
                        if character.id == char.id:
                            sel_bool = True
                else:
                    if x == selected:
                        sel_bool = True

                # print(f"{row['name']}: x: {x}, selected: {selected}")

                if sel_bool:
                    selector = ">>"
                if character.player or gm:
                    if character.temp_hp != 0:
                        string = (
                            f"{selector}  {init_num} {str(character.char_name).title()}:"
                            f" {character.current_hp}/{character.max_hp} ({character.temp_hp} Temp)\n"
                        )
                    else:
                        string = (
                            f"{selector}  {init_num} {str(character.char_name).title()}:"
                            f" {character.current_hp}/{character.max_hp}\n"
                        )
                else:
                    string = (
                        f"{selector}  {init_num} {str(character.char_name).title()}:"
                        f" {await character.calculate_hp()} \n"
                    )
                output_string += string

                for con_row in condition_list:
                    logging.info(f"BGT5: con_row in condition list {con_row.title} {con_row.id}")
                    # print(con_row)
                    await asyncio.sleep(0)
                    if gm or not con_row.counter:
                        if con_row.number is not None and con_row.number > 0:
                            if con_row.time:
                                time_stamp = datetime.fromtimestamp(con_row.number)
                                current_time = await get_time(self.ctx, guild=self.guild)
                                time_left = time_stamp - current_time
                                days_left = time_left.days
                                processed_minutes_left = divmod(time_left.seconds, 60)[0]
                                processed_hours_left = divmod(processed_minutes_left, 60)[0]
                                processed_minutes_left = divmod(processed_minutes_left, 60)[1]
                                processed_seconds_left = divmod(time_left.seconds, 60)[1]
                                if processed_seconds_left < 10:
                                    processed_seconds_left = f"0{processed_seconds_left}"
                                if processed_minutes_left < 10:
                                    processed_minutes_left = f"0{processed_minutes_left}"
                                if days_left != 0:
                                    con_string = (
                                        f"       {con_row.title}: {days_left} Days,"
                                        f" {processed_minutes_left}:{processed_seconds_left}\n "
                                    )
                                else:
                                    if processed_hours_left != 0:
                                        con_string = (
                                            f"       {con_row.title}:"
                                            f" {processed_hours_left}:{processed_minutes_left}:"
                                            f"{processed_seconds_left}\n"
                                        )
                                    else:
                                        con_string = (
                                            f"       {con_row.title}:"
                                            f" {processed_minutes_left}:{processed_seconds_left}\n"
                                        )
                            else:
                                con_string = f"       {con_row.title}: {con_row.number}\n"
                        else:
                            con_string = f"       {con_row.title}\n"

                    elif con_row.counter is True and sel_bool and row.player:
                        con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = ""
                    output_string += con_string

            output_string += "```"
            # print(output_string)
            return output_string
        except Exception as e:
            logging.info(f"block_get_tracker 2: {e}")
            return "ERROR"

    async def efficient_block_get_tracker(
        self, selected: int, gm: bool = False
    ):  # Probably should rename this eventually
        """
        This method formats the tracker as a complex string. This is the base tracker, with each subclass having a
        version specific to that RPG system.
        :param selected: (integer id of the current character)
        :param gm: bool True for GM tracker, false for player tracker
        :return: output string
        """
        logging.info("generic_block_get_tracker")
        # Get the datetime
        datetime_string = ""

        # Get the turn List for Block Initiative. If its in block we need the whole turn list and not just
        if self.guild.block and self.guild.initiative is not None:
            turn_list = await self.get_turn_list()
            block = True
        else:
            block = False
        logging.info(f"BGT2: round: {self.guild.round}")

        # Code for appending the inactive list onto the init_list
        total_list = await self.get_init_list(self.ctx, self.engine, guild=self.guild)
        active_length = len(total_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await self.get_inactive_list()
        if len(inactive_list) > 0:
            total_list.extend(inactive_list)
            # print(f'Total Length: {len(init_list)}')

        # Generate the data_time string if timekeeper is active
        try:
            if self.guild.timekeeping:
                datetime_string = (
                    f" {await output_datetime(self.ctx, self.engine, self.bot, guild=self.guild)}"
                    "\n________________________\n"
                )
        except NoResultFound:
            if self.ctx is not None:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
            logging.info("Channel Not Set Up")
        except Exception as e:
            logging.error(f"get_tracker: {e}")
            if self.ctx is not None and self.bot is not None:
                report = ErrorReport(self.ctx, "get_tracker", e, self.bot)
                await report.report()

        try:
            Condition = await get_condition(self.ctx, id=self.guild.id)

            # if round = 0, were not in initiative, and act accordingly
            if self.guild.round != 0:
                round_string = f"Round: {self.guild.round}"
            else:
                round_string = ""

            output_string = f"```{datetime_string}Initiative: {round_string}\n"
            gm_output_string = f"```{datetime_string}Initiative: {round_string}\n"
            # Iterate through the init list
            for x, row in enumerate(total_list):
                character = await get_character(row.name, self.ctx, guild=self.guild)
                logging.info(f"BGT4: for row x in enumerate(row_data): {x}")
                # If there is an inactive list, and this is at the transition, place the line marker
                if len(total_list) > active_length and x == active_length:
                    output_string += "-----------------\n"  # Put in the divider
                    gm_output_string += "-----------------\n"

                # Get all of the visible condition for the character
                async with async_session() as session:
                    result = await session.execute(
                        select(Condition)
                        .where(Condition.character_id == character.id)
                        .where(Condition.visible == true())
                    )
                    condition_list = result.scalars().all()

                await asyncio.sleep(0)  # ensure the loop doesn't lock the bot in case of an error
                sel_bool = False
                selector = "  "

                # don't show an init if not in combat
                if character.init == 0 or character.active is False:
                    init_num = ""
                else:
                    if character.init <= 9:
                        init_num = f" {character.init}"
                    else:
                        init_num = f"{character.init}"

                if block:
                    for (
                        char
                    ) in (
                        turn_list
                    ):  # ignore this error, turn list is gotten if block is true, so this will always apply
                        # print(f'character.id = {character.id}')
                        if character.id == char.id:
                            sel_bool = True
                else:
                    if x == selected:
                        sel_bool = True

                # print(f"{row['name']}: x: {x}, selected: {selected}")

                if sel_bool:
                    selector = ">>"

                if character.temp_hp != 0:
                    string = (
                        f"{selector}  {init_num} {str(character.char_name).title()}:"
                        f" {character.current_hp}/{character.max_hp} ({character.temp_hp} Temp)\n"
                    )
                else:
                    string = (
                        f"{selector}  {init_num} {str(character.char_name).title()}:"
                        f" {character.current_hp}/{character.max_hp}\n"
                    )
                gm_output_string += string
                if character.player:
                    output_string += string
                else:
                    string = (
                        f"{selector}  {init_num} {str(character.char_name).title()}:"
                        f" {await character.calculate_hp()} \n"
                    )
                    output_string += string

                for con_row in condition_list:
                    logging.info(f"BGT5: con_row in condition list {con_row.title} {con_row.id}")
                    # print(con_row)
                    await asyncio.sleep(0)

                    if con_row.number is not None and con_row.number > 0:
                        if con_row.time:
                            time_stamp = datetime.fromtimestamp(con_row.number)
                            current_time = await get_time(self.ctx, guild=self.guild)
                            time_left = time_stamp - current_time
                            days_left = time_left.days
                            processed_minutes_left = divmod(time_left.seconds, 60)[0]
                            processed_hours_left = divmod(processed_minutes_left, 60)[0]
                            processed_minutes_left = divmod(processed_minutes_left, 60)[1]
                            processed_seconds_left = divmod(time_left.seconds, 60)[1]
                            if processed_seconds_left < 10:
                                processed_seconds_left = f"0{processed_seconds_left}"
                            if processed_minutes_left < 10:
                                processed_minutes_left = f"0{processed_minutes_left}"
                            if days_left != 0:
                                con_string = (
                                    f"       {con_row.title}: {days_left} Days,"
                                    f" {processed_minutes_left}:{processed_seconds_left}\n "
                                )
                            else:
                                if processed_hours_left != 0:
                                    con_string = (
                                        f"       {con_row.title}:"
                                        f" {processed_hours_left}:{processed_minutes_left}:"
                                        f"{processed_seconds_left}\n"
                                    )
                                else:
                                    con_string = (
                                        f"       {con_row.title}: {processed_minutes_left}:{processed_seconds_left}\n"
                                    )
                        else:
                            con_string = f"       {con_row.title}: {con_row.number}\n"
                    else:
                        con_string = f"       {con_row.title}\n"
                    gm_output_string += con_string
                    if con_row.counter is True and sel_bool and row.player:
                        output_string += con_string
                    elif not con_row.counter:
                        output_string += con_string

            output_string += "```"
            gm_output_string += "```"
            # print(output_string)
            return {"tracker": output_string, "gm_tracker": gm_output_string}
        except Exception as e:
            logging.info(f"block_get_tracker 2: {e}")
            return "ERROR"

    async def raw_tracker_output(self, selected: int):
        tracker_output = {"tracker": [], "round": "", "gm": self.guild.gm}

        if self.guild.block and self.guild.initiative is not None:
            turn_list = await self.get_turn_list()
            block = True
        else:
            block = False

        # Code for appending the inactive list onto the init_list
        total_list = await self.get_init_list(self.ctx, self.engine, guild=self.guild)
        active_length = len(total_list)
        # print(f'Active Length: {active_length}')
        inactive_list = await self.get_inactive_list()
        if len(inactive_list) > 0:
            total_list.extend(inactive_list)

        try:
            if self.guild.timekeeping:
                tracker_output["datetime"] = (
                    f"{await output_datetime(self.ctx, self.engine, self.bot, guild=self.guild)}"
                )
        except NoResultFound:
            logging.info("Channel Not Set Up")
        except Exception as e:
            logging.error(f"raw_tracker_output: {e}")

        Condition = await get_condition(self.ctx, id=self.guild.id)

        # if round = 0, were not in initiative, and act accordingly
        if self.guild.round != 0:
            tracker_output["round"] = f"{self.guild.round}"

        try:
            for x, row in enumerate(total_list):
                character = await get_character(row.name, self.ctx, guild=self.guild)

                if len(total_list) > active_length and x == active_length:
                    tracker_output["tracker"].append("Inactive List")  # Put in the divider

                output_obj = {
                    "init": "",
                    "selected": False,
                    "conditions": [],
                }

                async with async_session() as session:
                    result = await session.execute(
                        select(Condition)
                        .where(Condition.character_id == character.id)
                        .where(Condition.visible == true())
                    )
                    condition_list = result.scalars().all()

                await asyncio.sleep(0)  # ensure the loop doesn't lock the bot in case of an error
                sel_bool = False

                # don't show an init if not in combat
                if character.init == 0 or character.active is False:
                    init_num = ""
                else:
                    init_num = f"{character.init}"

                if block:
                    for (
                        char
                    ) in (
                        turn_list
                    ):  # ignore this error, turn list is gotten if block is true, so this will always apply
                        # print(f'character.id = {character.id}')
                        if character.id == char.id:
                            sel_bool = True
                else:
                    if x == selected:
                        sel_bool = True

                # print(f"{row['name']}: x: {x}, selected: {selected}")

                output_obj["init"] = (init_num,)
                output_obj["selected"] = sel_bool

                character_output = {
                    "hp": character.current_hp,
                    "max_hp": character.max_hp,
                    "temp_hp": character.temp_hp,
                    "name": character.char_name,
                    "pc": character.player,
                    "hp_string": str(await character.calculate_hp()),
                    "pic": character.pic,
                }

                try:
                    character_output["ac"] = character.ac_total
                except AttributeError:
                    pass

                output_obj["character"] = character_output

                for con_row in condition_list:
                    condition_object = {"counter": con_row.counter, "title": con_row.title}

                    if con_row.time:
                        time_stamp = datetime.fromtimestamp(con_row.number)
                        current_time = await get_time(self.ctx, guild=self.guild)
                        time_left = time_stamp - current_time
                        days_left = time_left.days
                        processed_minutes_left = divmod(time_left.seconds, 60)[0]
                        processed_hours_left = divmod(processed_minutes_left, 60)[0]
                        processed_minutes_left = divmod(processed_minutes_left, 60)[1]
                        processed_seconds_left = divmod(time_left.seconds, 60)[1]
                        if processed_seconds_left < 10:
                            processed_seconds_left = f"0{processed_seconds_left}"
                        if processed_minutes_left < 10:
                            processed_minutes_left = f"0{processed_minutes_left}"
                        if days_left != 0:
                            con_string = f"{days_left} Days, {processed_minutes_left}:{processed_seconds_left}"
                        else:
                            if processed_hours_left != 0:
                                con_string = f"{processed_hours_left}:{processed_minutes_left}:{processed_seconds_left}"
                            else:
                                con_string = f"{processed_minutes_left}:{processed_seconds_left}"
                        condition_object["duration"] = con_string
                        condition_object["time"] = True
                    else:
                        condition_object["duration"] = con_row.number
                        condition_object["time"] = False
                    try:
                        condition_object["value"] = con_row.value
                    except AttributeError:
                        condition_object["value"] = con_row.number

                    try:
                        if con_row.action != "":
                            condition_object["data"] = True
                        else:
                            condition_object["data"] = False
                    except AttributeError:
                        condition_object["data"] = False

                    output_obj["conditions"].append(condition_object)
                tracker_output["tracker"].append(output_obj)

        except Exception:
            pass

        return tracker_output

    # Note: Works backwards
    # This is the turn list, a list of all of characters that are part of the turn in block initiative
    async def get_turn_list(self):
        """
        Generates a list of characters in the initiative block.  Starts at the end (as this is where it has ended up via
        the advance turn function,0 and works backwards.
        :return: list of character models in the given turn in block initiative
        """

        # Note, this could be updated to only show characters who haven't passed their turn yet. Not sure if its a
        # benefit from a gameplay usability perspective though.
        # Implimented on a trial basis

        logging.info("get_turn_list")
        turn_list = []
        block_done = False
        try:
            logging.info(f"GTL1: guild: {self.guild.id}")
            iteration = 0
            init_pos = self.guild.initiative
            if init_pos is None:
                return []
            # print(f"init_pos: {init_pos}")
            # print(init_pos)
            length = len(self.init_list)
            while not block_done:
                # This removes characters which have finished their turn
                char = self.init_list[init_pos]
                if int(char.user) in self.guild.block_data:
                    turn_list.append(self.init_list[init_pos])

                player_status = self.init_list[init_pos].player
                if init_pos == 0:
                    if player_status != self.init_list[length - 1].player:
                        block_done = True
                else:
                    if player_status != self.init_list[init_pos - 1].player:
                        block_done = True

                init_pos -= 1
                if init_pos < 0:
                    if self.guild.round != 1:  # Don't loop back to the end on the first round
                        init_pos = length - 1
                    else:
                        block_done = True
                iteration += 1
                if iteration >= length:
                    block_done = True
            logging.info("GTL2")
            return turn_list
        except Exception as e:
            logging.warning(f"get_turn_list: {e}")
            return []

    # Post a new initiative tracker and updates the pinned trackers
    async def block_post_init(self):
        """
        Post the initiative tracker in the active player channel. This is used for when turns advance.

        :return: No return value
        """
        logging.info("base block_post_init")
        # Query the initiative position for the tracker and post it

        try:
            if self.guild.block:
                block = True
                # print(f"block_post_init: \n {turn_list}")
            else:
                block = False

            # print(init_list)
            trackers = await self.efficient_block_get_tracker(self.guild.initiative)
            tracker_string = trackers["tracker"]
            # print(tracker_string)
            try:
                logging.info("BPI2")
                ping_string = ""
                if block:
                    for player in self.guild.block_data:
                        try:
                            user = self.bot.get_user(player)
                            ping_string += f"{user.mention}, "
                        except Exception:
                            ping_string += "Unknown User, "
                    ping_string += "it's your turn.\n"

                    # for character in turn_list:
                    #     await asyncio.sleep(0)
                    #     user = self.bot.get_user(character.user)
                    #     ping_string += f"{user.mention}, "
                    # ping_string += "it's your turn.\n"
                else:
                    user = self.bot.get_user(self.init_list[self.guild.initiative].user)
                    ping_string += f"{user.mention}, it's your turn.\n"
            except Exception as e:
                logging.error(f"post_init: {e}")
                ping_string = ""

            # Check for systems:

            view = discord.ui.View(timeout=None)
            self.Refresh_Button = self.InitRefreshButton(self.ctx, self.bot, guild=self.guild)
            self.Next_Button = self.NextButton(self.bot, guild=self.guild)
            view.add_item(self.Refresh_Button)
            view.add_item(self.Next_Button)
            # Always post the tracker to the player channel
            if self.ctx is not None:
                if self.ctx.channel.id == self.guild.tracker_channel:
                    tracker_msg = await self.ctx.send_followup(f"{tracker_string}\n{ping_string}", view=view)
                else:
                    await self.bot.get_channel(self.guild.tracker_channel).send(
                        f"{tracker_string}\n{ping_string}", view=view
                    )
                    tracker_msg = await self.ctx.send_followup("Initiative Advanced.")
                    logging.info("BPI5")
            else:
                tracker_msg = await self.bot.get_channel(self.guild.tracker_channel).send(
                    f"{tracker_string}\n{ping_string}", view=view
                )
                logging.info("BPI5 Guild")

            if self.guild.tracker is not None:
                channel = self.bot.get_channel(self.guild.tracker_channel)
                try:
                    message = await channel.fetch_message(self.guild.tracker)
                    await message.edit(content=tracker_string)
                except discord.errors.NotFound:
                    await self.set_pinned_tracker(channel, gm=False)
            if self.guild.gm_tracker is not None:
                gm_tracker_display_string = trackers["gm_tracker"]
                gm_channel = self.bot.get_channel(self.guild.gm_tracker_channel)
                try:
                    gm_message = await gm_channel.fetch_message(self.guild.gm_tracker)
                    await gm_message.edit(content=gm_tracker_display_string)
                except discord.errors.NotFound:
                    await self.set_pinned_tracker(gm_channel, gm=True)

            async with async_session() as session:
                if self.ctx is None:
                    result = await session.execute(select(Global).where(Global.id == self.guild.id))
                else:
                    result = await session.execute(
                        select(Global).where(
                            or_(
                                Global.tracker_channel == self.ctx.interaction.channel_id,
                                Global.gm_tracker_channel == self.ctx.interaction.channel_id,
                            )
                        )
                    )
                guild = result.scalars().one()
                try:
                    if guild.last_tracker is not None:
                        tracker_channel = self.bot.get_channel(guild.tracker_channel)
                        old_tracker_msg = await tracker_channel.fetch_message(guild.last_tracker)
                        await old_tracker_msg.edit(view=None)
                except Exception as e:
                    logging.warning(e)
                guild.last_tracker = tracker_msg.id
                await session.commit()
                await self.update()
        except NoResultFound:
            if self.ctx is not None:
                await self.ctx.channel.send(error_not_initialized, delete_after=30)
        except Exception as e:
            logging.error(f"block_post_init: {e}")
            if self.ctx is not None:
                report = ErrorReport(self.ctx, "block_post_init", e, self.bot)
                await report.report()

        await self.websocket_stream()

    # Updates the active initiative tracker (not the pinned tracker)
    async def update_pinned_tracker(self):
        """
        Updates the pinned trackers. Pulls a new, updated tracker and edits the pinned trackers.

        :return: No return value
        """
        logging.info("update_pinned_tracker")

        # Query the initiative position for the tracker and post it
        try:
            logging.info(f"BPI1: guild: {self.guild.id}")

            if self.guild.block:
                block = True
            else:
                block = False

            # Fix the Tracker if needed, then refresh the guild
            await self.init_integrity()
            await self.update()
            trackers = await self.efficient_block_get_tracker(self.guild.initiative)
            tracker_string = trackers["tracker"]

            try:
                logging.info("BPI2")
                ping_string = ""
                if block:
                    for player in self.guild.block_data:
                        try:
                            user = self.bot.get_user(player)
                            ping_string += f"{user.mention}, "
                        except Exception:
                            ping_string += "Unknown User, "
                    ping_string += "it's your turn.\n"

                else:
                    user = self.bot.get_user(self.init_list[self.guild.initiative].user)
                    ping_string += f"{user.mention}, it's your turn.\n"
            except Exception:
                # print(f'post_init: {e}')
                ping_string = ""
            view = discord.ui.View(timeout=None)
            # Check for systems:
            if self.guild.last_tracker is not None:
                self.Refresh_Button = self.InitRefreshButton(self.ctx, self.bot, guild=self.guild)
                self.Next_Button = self.NextButton(self.bot, guild=self.guild)
                view.add_item(self.Refresh_Button)
                view.add_item(self.Next_Button)
                if self.guild.last_tracker is not None:
                    tracker_channel = self.bot.get_channel(self.guild.tracker_channel)
                    edit_message = await tracker_channel.fetch_message(self.guild.last_tracker)
                    await edit_message.edit(
                        content=f"{tracker_string}\n{ping_string}",
                        view=view,
                    )
            if self.guild.tracker is not None:
                try:
                    channel = self.bot.get_channel(self.guild.tracker_channel)
                    message = await channel.fetch_message(self.guild.tracker)
                    await message.edit(content=tracker_string)
                except Exception:
                    logging.warning(f"Invalid Tracker: {self.guild.id}")
                    channel = self.bot.get_channel(self.guild.tracker_channel)
                    await self.set_pinned_tracker(channel)

            if self.guild.gm_tracker is not None:
                try:
                    gm_tracker_display_string = trackers["gm_tracker"]
                    gm_channel = self.bot.get_channel(self.guild.gm_tracker_channel)
                    gm_message = await gm_channel.fetch_message(self.guild.gm_tracker)
                    await gm_message.edit(content=gm_tracker_display_string)
                except Exception:
                    logging.warning(f"Invalid GMTracker: {self.guild.id}")
                    channel = self.bot.get_channel(self.guild.gm_tracker_channel)
                    await self.set_pinned_tracker(channel, gm=True)

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
        except Exception as e:
            logging.error(f"update_pinned_tracker: {e}")
            report = ErrorReport(self.ctx, "update_pinned_tracker", e, self.bot)
            await report.report()

        await self.websocket_stream()

    async def websocket_stream(self):
        try:
            if await socket.library_check(self.guild.id):
                output_model = await self.raw_tracker_output(self.guild.initiative)

                guild_info = {
                    "id": self.guild.id,
                    "system": self.guild.system,
                    "gm": self.guild.gm,
                    "members": self.guild.members,
                }

                output = {
                    "guild": self.guild.id,
                    "output": output_model,
                    "init_pos": self.guild.initiative,
                    "guild_info": guild_info,
                }
                await socket.stream_channel(self.guild.id, output, "tracker")
        except Exception as e:
            logging.error(f"websocket_stream {e}")

    async def repost_trackers(self):
        """
        Posts new trackers in the player and gm channel and then pins them.

        :return: bool. True if succssful, false if unsuccessful
        """
        logging.info("repost_trackers")
        try:
            channel = self.bot.get_channel(self.guild.tracker_channel)
            gm_channel = self.bot.get_channel(self.guild.gm_tracker_channel)
            await self.set_pinned_tracker(channel)  # set the tracker in the player channel
            await self.set_pinned_tracker(gm_channel, gm=True)  # set up the gm_track in the GM channel
            return True
        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"repost_trackers: {e}")
            report = ErrorReport(self.ctx, "repost_trackers", e, self.bot)
            await report.report()
            return False

    # Function sets the pinned trackers and records their position in the Global table.
    async def set_pinned_tracker(self, channel: discord.TextChannel, gm=False):
        """
        Posts a tracker and then pins it
        :param channel: Discord channel
        :param gm: bool. Default false. If true, posts a gm tracker.
        :return: bool. True for success, false for failure
        """

        logging.info("set_pinned_tracker")
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Global).where(
                        or_(
                            Global.tracker_channel == self.ctx.interaction.channel_id,
                            Global.gm_tracker_channel == self.ctx.interaction.channel_id,
                        )
                    )
                )
                guild = result.scalars().one()

                try:
                    init_pos = int(guild.initiative)
                except Exception:
                    init_pos = None
                tracker = await self.efficient_block_get_tracker(init_pos, gm=gm)
                if gm:
                    display_string = tracker["gm_tracker"]
                else:
                    display_string = tracker["tracker"]
                interaction = await self.bot.get_channel(channel.id).send(display_string)
                await interaction.pin()
                if gm:
                    guild.gm_tracker = interaction.id
                    guild.gm_tracker_channel = channel.id
                else:
                    guild.tracker = interaction.id
                    guild.tracker_channel = channel.id
                await session.commit()
            return True
        except Exception as e:
            logging.warning(f"set_pinned_tracker: {e}")
            report = ErrorReport(self.ctx, "set_pinned_tracker", e, self.bot)
            await report.report()
            return False

    async def check_cc(self):
        """
        Checks to see if any of the conditions have expired due to time and clears them out.
        Not for use while in initiative.
        Called by advancing time.

        :return: No return value
        """
        logging.info("check_cc")
        current_time = await get_time(self.ctx, guild=self.guild)

        Tracker = await get_tracker(self.ctx, id=self.guild.id)
        Condition = await get_condition(self.ctx, id=self.guild.id)

        async with async_session() as session:
            result = await session.execute(select(Condition).where(Condition.time == true()))
            con_list = result.scalars().all()

        for row in con_list:
            await asyncio.sleep(0)
            time_stamp = datetime.fromtimestamp(row.number)
            time_left = time_stamp - current_time
            if time_left.total_seconds() <= 0:
                async with async_session() as session:
                    result = await session.execute(select(Tracker).where(Tracker.id == row.character_id))
                    character = result.scalars().one()
                async with async_session() as session:
                    await session.delete(row)
                    await session.commit()
                if self.ctx is not None:
                    await self.ctx.channel.send(f"{row.title} removed from {character.name}")
                else:
                    tracker_channel = self.bot.get_channel(self.guild.tracker_channel)
                    tracker_channel.send(f"{row.title} removed from {character.name}")

    class InitRefreshButton(discord.ui.Button):
        """
        Refresh button for the tracker
        """

        def __init__(self, ctx: discord.ApplicationContext, bot, guild=None):
            self.ctx = ctx
            self.engine = Backend.Database.engine.engine
            self.bot = bot
            self.guild = guild
            super().__init__(style=discord.ButtonStyle.primary, emoji="🔁")

        async def callback(self, interaction: discord.Interaction):
            try:
                await interaction.response.send_message("Refreshed", ephemeral=True)

                Tracker_model = Tracker(
                    self.ctx,
                    self.engine,
                    await get_init_list(self.ctx, self.engine, self.guild),
                    self.bot,
                    guild=self.guild,
                )
                await Tracker_model.update_pinned_tracker()
            except Exception as e:
                # print(f"Error: {e}")
                logging.info(e)

    class NextButton(discord.ui.Button):
        """
        Next button for the tracker
        """

        def __init__(self, bot, guild=None):
            self.engine = Backend.Database.engine.engine
            self.bot = bot
            self.guild = guild
            super().__init__(
                style=discord.ButtonStyle.primary, emoji="➡️" if not guild.block or len(guild.block_data) < 2 else "✔"
            )

        async def callback(self, interaction: discord.Interaction):
            try:
                Tracker_Model = Tracker(
                    None,
                    self.engine,
                    await get_init_list(None, self.engine, self.guild),
                    self.bot,
                    guild=self.guild,
                )
                await Tracker_Model.block_next(interaction)
            except Exception as e:
                # print(f"Error: {e}")
                logging.info(e)
