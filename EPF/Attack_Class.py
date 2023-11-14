import logging

import d20
import discord
from sqlalchemy.exc import NoResultFound

from EPF.EPF_Character import EPF_Character, get_EPF_Character
from EPF.EPF_resists import damage_calc_resist, roll_dmg_resist
from PF2e.pf2_functions import PF2_eval_succss
from database_operations import engine
from error_handling_reporting import error_not_initialized
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers
from utils.utils import get_guild


async def get_attack(character, attack_name, ctx, guild=None):
    guild = await get_guild(ctx, guild)
    CharacterModel = await get_character(character, ctx, guild=guild, engine=engine)
    try:
        attack_data = await CharacterModel.get_weapon(attack_name)
    except Exception:
        attack_data = ""
    return Attack(ctx, guild, CharacterModel, attack_name, attack_data)


class Attack:
    def __init__(self, ctx, guild, character: EPF_Character, attack_name: str, attack_data: dict):
        print("Initializing Attack")
        self.ctx = ctx
        self.guild = guild
        self.character = character
        self.attack_name = attack_name
        self.attack = attack_data
        self.output = None

        if type(attack_data) == dict:
            if "complex" in attack_data.keys():
                if attack_data["complex"]:
                    self.complex = True
                else:
                    self.complex = False
            else:
                self.complex = False
        else:
            self.complex = False

        if self.complex:
            self.attack_type = attack_data["type"]["value"]
        else:
            self.attack_type = None
        print("Success")

    def success_color(self, success_string):
        if success_string == "Critical Success":
            color = discord.Color.gold()
        elif success_string == "Success":
            color = discord.Color.green()
        elif success_string == "Failure":
            color = discord.Color.red()
        else:
            color = discord.Color.dark_red()

        return color

    async def roll_attack(self, target, vs, attack_modifier, target_modifier):
        if self.complex:
            return await self.complex_attack(target, vs, attack_modifier, target_modifier)
        else:
            return await self.simple_attack(target, vs, attack_modifier, target_modifier)

    async def simple_attack(self, target, vs, attack_modifier, target_modifier):
        print("simple attack")
        try:
            roll_string: str = f"{self.attack_name}{ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)
        except Exception:
            roll_string = f"({await self.character.get_roll(self.attack_name)}){ParseModifiers(attack_modifier)}"
            dice_result = d20.roll(roll_string)

        opponent = await get_character(target, self.ctx, guild=self.guild, engine=engine)
        goal_value = await opponent.get_dc(vs)

        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"attack: {e}")
            return "Error"

        success_string = PF2_eval_succss(dice_result, goal_result)

        embed = discord.Embed(
            title=f"{self.character.char_name} vs {opponent.char_name}",
            fields=[
                discord.EmbedField(
                    name=self.attack_name,
                    value=(
                        f"{self.character.char_name} rolls {self.attack_name} vs"
                        f" {opponent.char_name} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
                    ),
                )
            ],
            color=self.success_color(success_string),
        )
        embed.set_thumbnail(url=self.character.pic)
        self.output = embed

        return self.output

    async def complex_attack(self, target, vs, attack_modifier, target_modifier):
        return []

    async def save(self, target, dc, modifier):
        if target is None:
            embed = discord.Embed(
                title=self.character.char_name,
                fields=[discord.EmbedField(name=self.attack_name, value="Invalid Target")],
            )
            self.output = embed
            return self.output

        opponent = await get_EPF_Character(target, self.ctx, guild=self.guild, engine=engine)

        orig_dc = dc

        if dc is None:
            dc = await self.character.get_dc("DC")
        try:
            dice_result = d20.roll(f"{await opponent.get_roll(self.attack_name)}{ParseModifiers(modifier)}")
            goal_result = d20.roll(f"{dc}")
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False

        try:
            success_string = PF2_eval_succss(dice_result, goal_result)

            if self.character.char_name == target:
                output_string = (
                    f"{self.character.char_name} makes a"
                    f" {self.attack_name} save!\n{dice_result}\n{success_string if orig_dc else ''}"
                )
            else:
                output_string = (
                    f"{opponent.char_name} makes a {self.attack_name} save!\n{self.character.char_name} forced the"
                    f" save.\n{dice_result}\n{success_string}"
                )

            embed = discord.Embed(
                title=(
                    f"{self.character.char_name} vs {opponent.char_name}"
                    if self.character.char_name != target
                    else f"{self.character.char_name}"
                ),
                fields=[discord.EmbedField(name=self.attack_name, value=output_string)],
                color=self.success_color(success_string),
            )
            embed.set_thumbnail(url=self.character.pic)
            self.output = embed
            return self.output

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False

    async def damage(self, target, modifier, healing, damage_type: str, crit=False):
        Target_Model = await get_character(target, self.ctx, engine=engine, guild=self.guild)
        weapon = None

        if self.complex:
            # TODO Add complex damage roll
            pass
        else:
            try:
                roll_result: d20.RollResult = d20.roll(f"({self.attack_name}){ParseModifiers(modifier)}")
                dmg = roll_result.total
                if not healing:
                    dmg = await damage_calc_resist(dmg, damage_type, Target_Model, weapon=weapon)
                roll_string = f"{roll_result} {damage_type}"
            except Exception:
                try:
                    dmg_output, total_damage = await roll_dmg_resist(
                        self.character, Target_Model, self.attack_name, crit, modifier, dmg_type_override=damage_type
                    )
                    roll_string = ""
                    for item in dmg_output:
                        roll_string += f"{item['dmg_output_string']} {item['dmg_type'].title()}\n"
                    dmg = total_damage
                except Exception:
                    try:
                        roll_result = d20.roll(
                            f"{await self.character.get_roll(self.attack_name)}{ParseModifiers(modifier)}"
                        )
                        dmg = roll_result.total
                        if not healing:
                            dmg = await damage_calc_resist(dmg, damage_type, Target_Model, weapon=weapon)
                        roll_string = f"{roll_result} {damage_type}"
                    except Exception:
                        roll_result = d20.roll("0 [Error]")
                        dmg = roll_result.total
                        roll_string = roll_result

        await Target_Model.change_hp(dmg, healing, post=False)
        output_string = (
            f"{self.character.char_name} {'heals' if healing else 'damages'}  {target} for: \n{roll_string}"
            f"\n{f'{dmg} Damage' if not healing else f'{dmg} Healed'}\n"
            f"{await Target_Model.calculate_hp()}"
        )

        embed = discord.Embed(
            title=f"{self.character.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=self.attack_name, value=output_string)],
        )
        embed.set_thumbnail(url=self.character.pic)

        self.output = embed

        return self.output
