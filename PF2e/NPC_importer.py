# NPC_importer.py
import asyncio
import os

import discord
from discord.ui import View
from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import initiative
from database_models import (
    get_macro,
    get_condition,
    get_tracker,
    NPC,
)
from dice_roller import DiceRoller

# imports

# define global variables

load_dotenv(verbose=True)
if os.environ["PRODUCTION"] == "True":
    TOKEN = os.getenv("TOKEN")
    USERNAME = os.getenv("Username")
    PASSWORD = os.getenv("Password")
    HOSTNAME = os.getenv("Hostname")
    PORT = os.getenv("PGPort")
else:
    TOKEN = os.getenv("BETA_TOKEN")
    USERNAME = os.getenv("BETA_Username")
    PASSWORD = os.getenv("BETA_Password")
    HOSTNAME = os.getenv("BETA_Hostname")
    PORT = os.getenv("BETA_PGPort")

GUILD = os.getenv("GUILD")
SERVER_DATA = os.getenv("SERVERDATA")
DATABASE = os.getenv("DATABASE")


async def npc_lookup(ctx: discord.ApplicationContext, engine, lookup_engine, bot, name: str, lookup: str, elite: str):
    async_session = sessionmaker(lookup_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(NPC).where(func.lower(NPC.name).contains(lookup.lower())))
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
        if self.elite == "elite":
            if self.data.level <= 1:
                hp_mod = 10
            elif self.data.level <= 4:
                hp_mod = 15
            elif self.data.level <= 19:
                hp_mod = 20
            else:
                hp_mod = 30
            stat_mod = 2
        if self.elite == "weak":
            if self.data.level <= 1:
                hp_mod = -10
            elif self.data.level <= 4:
                hp_mod = -15
            elif self.data.level <= 19:
                hp_mod = -20
            else:
                hp_mod = -30
            stat_mod = -2

        try:
            dice = DiceRoller('')
            async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            guild = await initiative.get_guild(self.ctx, None)
            # print(guild.initiative)
            # print(int(self.data.init)+stat_mod)
            initiative_num = 0
            if guild.initiative is not None:
                try:
                    # print(f"Init: {init}")
                    initiative_num = int(self.data.init) + stat_mod
                    print(initiative_num)
                except Exception:
                    try:
                        if self.elite == "weak":
                            roll = await dice.plain_roll(f"{self.data.init}{stat_mod}")
                        else:
                            roll = await dice.plain_roll(f"{self.data.init}+{stat_mod}")
                        initiative_num = roll[1]
                        print(initiative_num)
                        if type(initiative_num) != int:
                            initiative_num = 0
                    except Exception:
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
                        temp_hp=0,
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
                    title="AC",
                    number=self.data.ac + stat_mod,
                    counter=True,
                    visible=False
                    )
                )
                session.add(Condition(
                    character_id=character.id,
                    title="Fort",
                    number=self.data.fort + stat_mod,
                    counter=True,
                    visible=False,
                  )
                )
                session.add(Condition(
                    character_id=character.id,
                    title="Reflex",
                    number=self.data.reflex + stat_mod,
                    counter=True,
                    visible=False,
                    )
                )
                session.add(Condition(
                    character_id=character.id,
                    title="Will",
                    number=self.data.will + stat_mod,
                    counter=True,
                    visible=False,
                    )
                )
                session.add(Condition(
                    character_id=character.id,
                    title="DC",
                    number=self.data.dc + stat_mod,
                    counter=True,
                    visible=False)
                )
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

            await initiative.update_pinned_tracker(self.ctx, self.engine, self.bot)
            output_string = f"{self.data.name} added as {self.name}"

            await self.ctx.channel.send(output_string)
        except Exception as e:
            await self.ctx.channel.send("Action Failed, please try again", delete_after=60)
