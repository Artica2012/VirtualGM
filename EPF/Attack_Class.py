import logging
from math import floor

import d20
import discord
import lark
from lark import Lark
from sqlalchemy.exc import NoResultFound

from EPF.EPF_Character import EPF_Character, get_EPF_Character
from EPF.EPF_resists import damage_calc_resist, roll_dmg_resist
from PF2e.pf2_functions import PF2_eval_succss
from database_operations import engine
from error_handling_reporting import error_not_initialized
from utils.Char_Getter import get_character
from utils.parsing import ParseModifiers
from utils.utils import get_guild


class AutoModel:
    def __init__(self, ctx, guild, character: EPF_Character, attack_name: str, attack_data: dict):
        self.ctx = ctx
        self.guild = guild
        self.character = character
        self.attack_name = attack_name
        self.attack = attack_data
        self.output = None

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

    async def pd(self, data, heighten, heighten_data, Target_Model):
        if "pd" in data.keys():
            # print(data["pd"])
            roll_string = data["pd"]["roll_string"]
            if heighten > 0:
                # print("heighten_data  ", heighten_data)
                for x in range(0, heighten):
                    for i in heighten_data["hpd"].keys():
                        roll_string = roll_string + " " + f"{heighten_data['hpd']['roll_string']}"
            save_string = ""
            if "save" in data["pd"]["save"]:
                save_string = f"/ dc{data['[pd']['save_value']} {data['pd']['save']}"
            action_string = f"pd {data['pd']['roll_string']} {data['pd']['dmg_type']} "
            await Target_Model.set_cc(
                f"Persistent {data['pd']['dmg_type']}", False, 0, "Round", False, data=f"{action_string} {save_string}"
            )
            # print(roll_string)
            # print(f"{action_string} {save_string}")

            embed = discord.Embed(
                title=Target_Model.char_name.title(),
                fields=[
                    discord.EmbedField(
                        name=f"Persistent {data['pd']['dmg_type']}", value=f"Persistent {data['pd']['dmg_type']} added."
                    )
                ],
                color=discord.Color.blurple(),
            )
            embed.set_thumbnail(url=self.character.pic)

            await self.ctx.channel.send(embed=embed)

        if "condition" in data.keys():
            embed = discord.Embed(
                title=data["condition"]["char_name"],
                fields=[
                    discord.EmbedField(
                        name=data["condition"]["title"].title(), value=f"{data['condition']['title'].title()} added."
                    )
                ],
                color=discord.Color.blurple(),
            )
            embed.set_thumbnail(url=self.character.pic)

            await self.ctx.channel.send(embed=embed)

    async def format_output(self, Attack_Data, Target_Model: EPF_Character):
        if Attack_Data.dmg_string is not None:
            dmg_output_string = f"{self.character.char_name} damages {Target_Model.char_name} for:"
            for item in Attack_Data.dmg_string:
                dmg_output_string += f"\n{item['dmg_output_string']} {item['dmg_type'].title()}"
            await Target_Model.change_hp(Attack_Data.total_damage, heal=False, post=False)
            if Target_Model.player:
                output = (
                    f"{Attack_Data.output}\n{dmg_output_string}\n{Target_Model.char_name} damaged for"
                    f" {Attack_Data.total_damage}.New HP: {Target_Model.current_hp}/{Target_Model.max_hp}"
                )
            else:
                output = (
                    f"{Attack_Data.output}\n{dmg_output_string}\n{Target_Model.char_name} damaged for"
                    f" {Attack_Data.total_damage}. {await Target_Model.calculate_hp()}"
                )
        else:
            output = Attack_Data.output

        embed = discord.Embed(
            title=f"{self.character.char_name} vs {Target_Model.char_name}",
            fields=[discord.EmbedField(name=self.attack_name.title(), value=output)],
            color=self.success_color(Attack_Data.success_string),
        )
        embed.set_thumbnail(url=self.character.pic)

        self.output = embed


async def get_attack(character, attack_name, ctx, guild=None):
    guild = await get_guild(ctx, guild)
    CharacterModel = await get_character(character, ctx, guild=guild, engine=engine)
    try:
        attack_data = await CharacterModel.get_weapon(attack_name)
    except Exception:
        attack_data = ""
    return Attack(ctx, guild, CharacterModel, attack_name, attack_data)


class Attack(AutoModel):
    def __init__(self, ctx, guild, character: EPF_Character, attack_name: str, attack_data: dict):
        # print("Initializing Attack")
        super().__init__(ctx, guild, character, attack_name, attack_data)

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
        # print("Success")

    async def roll_attack(self, target, vs, attack_modifier, target_modifier):
        if self.complex:
            return await self.complex_attack(target, vs, attack_modifier, target_modifier)
        else:
            return await self.simple_attack(target, vs, attack_modifier, target_modifier)

    async def simple_attack(self, target, vs, attack_modifier, target_modifier):
        # print("simple attack")
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
        output_string = (
            f"{self.character.char_name} rolls {self.attack_name} vs"
            f" {opponent.char_name} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
        )

        Data = Attack_Data(None, 0, success_string, output_string)

        await self.format_output(Data, opponent)

        return self.output

    async def complex_attack(self, target, vs, attack_modifier, target_modifier):
        Target_Model = await get_character(target, self.ctx, engine=engine, guild=self.guild)
        if self.attack_type == "attack":
            Data = await self.auto_complex_attack_attk(Target_Model, attack_modifier, target_modifier)
        else:
            Data = await self.auto_complex_save_attk(Target_Model, attack_modifier, target_modifier)

        await self.format_output(Data, Target_Model)

        return self.output

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

            Data = Attack_Data(None, 0, success_string, output_string)
            await self.format_output(Data, opponent)

            return self.output

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False

    async def damage(self, target, modifier, healing, damage_type: str, crit=False):
        Target_Model = await get_character(target, self.ctx, engine=engine, guild=self.guild)

        if self.complex:
            if crit:
                success_string = "Critical Success"
            else:
                success_string = "Success"
            if self.attack_type == "attack":
                Data = await self.auto_complex_attack_dmg(Target_Model, success_string, modifier, damage_type)
            elif self.attack_type == "save":
                Data = await self.auto_complex_save_dmg(Target_Model, success_string, modifier, damage_type)
            else:
                Data = Attack_Data(None, 0, success_string, "ERROR")
        else:
            Data = await self.simple_dmg(Target_Model, modifier, healing, damage_type, crit)

        await Target_Model.change_hp(Data.total_damage, healing, post=False)

        await self.format_output(Data, Target_Model)

        return self.output

    async def simple_dmg(self, Target_Model, modifier, healing, damage_type: str, crit=False, weapon=None):
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

        output_string = (
            f"{self.character.char_name} {'heals' if healing else 'damages'}  {Target_Model.char_name} for:"
            f" \n{roll_string}"
            f"\n{f'{dmg} Damage' if not healing else f'{dmg} Healed'}\n"
            f"{await Target_Model.calculate_hp()}"
        )

        return Attack_Data(None, dmg, None, output_string)

    async def auto(self, target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override):
        Target_Model = await get_character(target, self.ctx, engine=engine, guild=self.guild)

        if self.complex:
            Attack_Data = await self.auto_complex(
                target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override
            )
        else:
            Attack_Data = await self.auto_simple(
                target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override
            )

        await self.format_output(Attack_Data, Target_Model)

        return self.output

    async def auto_simple(self, target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override):
        Target_Model = await get_character(target, self.ctx, engine=engine, guild=self.guild)

        roll_string = f"({await self.character.get_roll(self.attack_name)})"
        dice_result = d20.roll(f"{roll_string}{ParseModifiers(attack_modifier)}")

        goal_value = Target_Model.ac_total
        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"auto: {e}")
            return "Error"

        # Format output string

        success_string = PF2_eval_succss(dice_result, goal_result)
        attk_output_string = (
            f"{self.character.name} attacks"
            f" {Target_Model.char_name} {'' if target_modifier == '' else f'(AC {target_modifier})'} with their"
            f" {self.attack_name}:\n{dice_result}\n{success_string}"
        )

        # Damage
        if success_string == "Critical Success" and "critical-hits" not in Target_Model.resistance.keys():
            dmg_string, total_damage = await roll_dmg_resist(
                self.character,
                Target_Model,
                self.attack_name,
                True,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
            )
        elif success_string == "Success" or success_string == "Critical Success":
            dmg_string, total_damage = await roll_dmg_resist(
                self.character,
                Target_Model,
                self.attack_name,
                False,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
            )
        else:
            dmg_string = None
            total_damage = 0

        return Attack_Data(dmg_string, total_damage, success_string, attk_output_string)

    async def auto_complex(self, target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override):
        # print("Complex Attack")
        # print(self.attack)

        Target_Model = await get_EPF_Character(target, self.ctx, guild=self.guild, engine=engine)

        if self.attack_type == "attack":
            Attk_Data = await self.auto_complex_attack_attk(Target_Model, attack_modifier, target_modifier)
            Dmg_Data = await self.auto_complex_attack_dmg(
                Target_Model, Attk_Data.success_string, dmg_modifier, dmg_type_override
            )
            return Attack_Data(Dmg_Data.dmg_string, Dmg_Data.total_damage, Dmg_Data.success_string, Attk_Data.output)
        elif self.attack_type == "save":
            # print("save")
            Attk_Data = await self.auto_complex_save_attk(Target_Model, attack_modifier, target_modifier)
            Dmg_Data = await self.auto_complex_save_dmg(
                Target_Model, Attk_Data.success_string, dmg_modifier, dmg_type_override
            )
            return Attack_Data(Dmg_Data.dmg_string, Dmg_Data.total_damage, Dmg_Data.success_string, Attk_Data.output)
        elif self.attack_type == "utility":
            return await self.auto_complex_utility(Target_Model)

    async def auto_complex_attack_attk(self, Target_Model: EPF_Character, attack_modifier, target_modifier):
        # Get roll depending on category - currently only kineticist
        if self.attack["category"] == "kineticist":
            roll_string = f"({await self.character.get_roll('class_dc')})"
        else:
            roll_string = f"({await self.character.get_roll('class_dc')})"

        # print(roll_string)
        dice_result = d20.roll(f"{roll_string}{ParseModifiers(attack_modifier)}")
        # print(dice_result)
        goal_value = Target_Model.ac_total

        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"auto: {e}")
            return "Error"

        success_string = PF2_eval_succss(dice_result, goal_result)

        attk_output_string = (
            f"{self.character.char_name} attacks"
            f" {Target_Model.char_name} {'' if target_modifier == '' else f'(AC {target_modifier})'} with their"
            f" {self.attack_name.title()}:\n{dice_result}\n{success_string}"
        )

        return Attack_Data(None, 0, success_string, attk_output_string)

    async def auto_complex_attack_dmg(
        self, Target_Model: EPF_Character, success_string: str, dmg_modifier, dmg_type_override
    ):
        # heightening code
        heighten_data, heighten = await self.heighten(Target_Model)

        if success_string == "Critical Success":
            if "critical success" in self.attack["effect"].keys():
                data = await automation_parse(self.attack["effect"]["critical success"], self.character, Target_Model)
                # print(data)
                data = self.heighten_calc(data, heighten, heighten_data)

                dmg_string, total_damage = await scripted_damage_roll_resists(
                    data, Target_Model, crit=True, flat_bonus=dmg_modifier, dmg_type_override=dmg_type_override
                )
                await self.pd(data, heighten, heighten_data, Target_Model)
            else:
                data = await automation_parse(self.attack["effect"]["success"], self.character, Target_Model)
                # print(data)
                data = self.heighten_calc(data, heighten, heighten_data)

                await self.pd(data, heighten, heighten_data, Target_Model)
                dmg_string, total_damage = await scripted_damage_roll_resists(
                    data, Target_Model, crit=True, flat_bonus=dmg_modifier, dmg_type_override=dmg_type_override
                )

        elif success_string == "Success":
            data = await automation_parse(self.attack["effect"]["success"], self.character, Target_Model)
            # print(data)
            data = self.heighten_calc(data, heighten, heighten_data)
            # print(data)
            await self.pd(data, heighten, heighten_data, Target_Model)
            dmg_string, total_damage = await scripted_damage_roll_resists(
                data, Target_Model, crit=False, flat_bonus=dmg_modifier, dmg_type_override=dmg_type_override
            )

        else:
            dmg_string = None
            total_damage = 0

        return Attack_Data(dmg_string, total_damage, success_string, "")

    async def auto_complex_save_attk(self, Target_Model: EPF_Character, attack_modifier, target_modifier):
        # Roll the save
        save = self.attack["type"]["save"]
        roll_string = f"({await Target_Model.get_roll(save)})"
        # print(roll_string)
        dice_result = d20.roll(f"{roll_string}{ParseModifiers(target_modifier)}")
        # print(dice_result)

        try:
            # Get the DC
            goal_string = f"{await self.character.get_dc('DC')}{ParseModifiers(attack_modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"auto: {e}")
            return "Error"

        success_string = PF2_eval_succss(dice_result, goal_result)

        attk_output_string = (
            f"{self.character.char_name} attacks"
            f" {Target_Model.char_name} {'' if target_modifier == '' else f'({save.title()} {target_modifier})'} with"
            f" their {self.attack_name.title()}:\n{self.character.char_name} forced a"
            f" {save.title()} save.\n{dice_result}\n{success_string}"
        )

        return Attack_Data(None, 0, success_string, attk_output_string)

    async def auto_complex_save_dmg(
        self, Target_Model: EPF_Character, success_string: str, dmg_modifier, dmg_type_override
    ):
        heighten_data, heighten = await self.heighten(Target_Model)
        dmg_string = None
        total_damage = 0

        if success_string == "Critical Success":
            if "critical success" in self.attack["effect"].keys():
                data = await automation_parse(self.attack["effect"]["critical success"], self.character, Target_Model)
                # print(data)
                data = self.heighten_calc(data, heighten, heighten_data)
                await self.pd(data, heighten, heighten_data, Target_Model)

                dmg_string, total_damage = await scripted_damage_roll_resists(
                    data, Target_Model, crit=False, flat_bonus=dmg_modifier, dmg_type_override=dmg_type_override
                )
            else:
                dmg_string = None
                total_damage = 0

        elif success_string == "Success":
            if "success" in self.attack["effect"].keys():
                data = await automation_parse(self.attack["effect"]["success"], self.character, Target_Model)
                # print(data)
                data = self.heighten_calc(data, heighten, heighten_data)
                # print(data)
                await self.pd(data, heighten, heighten_data, Target_Model)
                dmg_string, total_damage = await scripted_damage_roll_resists(
                    data, Target_Model, crit=False, flat_bonus=dmg_modifier, dmg_type_override=dmg_type_override
                )
            elif self.attack["type"]["type"] == "basic":
                data = await automation_parse(self.attack["effect"]["failure"], self.character, Target_Model)
                # print(data)
                data = self.heighten_calc(data, heighten, heighten_data)
                # print(data)
                await self.pd(data, heighten, heighten_data, Target_Model)
                dmg_string, total_damage = await scripted_damage_roll_resists(
                    data,
                    Target_Model,
                    crit=False,
                    flat_bonus=dmg_modifier,
                    dmg_type_override=dmg_type_override,
                    half=True,
                )
        elif success_string == "Failure":
            if "failure" in self.attack["effect"].keys():
                data = await automation_parse(self.attack["effect"]["failure"], self.character, Target_Model)
                # print(data)
                data = self.heighten_calc(data, heighten, heighten_data)
                await self.pd(data, heighten, heighten_data, Target_Model)
                dmg_string, total_damage = await scripted_damage_roll_resists(
                    data, Target_Model, crit=False, flat_bonus=dmg_modifier, dmg_type_override=dmg_type_override
                )
        elif success_string == "Critical Failure":
            if "critical failure" in self.attack["effect"].keys():
                data = await automation_parse(self.attack["effect"]["critical failure"], self.character, Target_Model)
                # print(data)
                data = self.heighten_calc(data, heighten, heighten_data)
                # print(data)
                await self.pd(data, heighten, heighten_data, Target_Model)
                dmg_string, total_damage = await scripted_damage_roll_resists(
                    data, Target_Model, crit=True, flat_bonus=dmg_modifier, dmg_type_override=dmg_type_override
                )
            else:
                data = await automation_parse(self.attack["effect"]["failure"], self.character, Target_Model)
                # print(data)
                data = self.heighten_calc(data, heighten, heighten_data)
                # print(data)
                dmg_string, total_damage = await scripted_damage_roll_resists(
                    data,
                    Target_Model,
                    crit=True,
                    flat_bonus=dmg_modifier,
                    dmg_type_override=dmg_type_override,
                )
                await self.pd(data, heighten, heighten_data, Target_Model)

        else:
            dmg_string = None
            total_damage = 0

        return Attack_Data(dmg_string, total_damage, success_string, "")

    async def auto_complex_utility(self, Target_Model: EPF_Character):
        heighten_data, heighten = await self.heighten(Target_Model)
        dmg_string = None
        total_damage = 0

        if "success" in self.attack["effect"].keys():
            data = await automation_parse(self.attack["effect"]["success"], self.character, Target_Model)
            # print(data)
            data = self.heighten_calc(data, heighten, heighten_data)
            # print(data)
            await self.pd(data, heighten, heighten_data, Target_Model)

        attk_output_string = f"{self.attack_name.title()} on {Target_Model.char_name}."

        return Attack_Data(dmg_string, total_damage, "Success", attk_output_string)

    async def heighten(self, Target_Model):
        # heightening code
        heighten_data = {}
        if "heighten" in self.attack.keys():
            if "interval" in self.attack["heighten"]:
                if self.character.character_model.level > self.attack["lvl"]:
                    heighten = floor(
                        (self.character.character_model.level - self.attack["lvl"])
                        / self.attack["heighten"]["interval"]
                    )
                else:
                    heighten = 0
                if heighten > 0:
                    heighten_data = await automation_parse(
                        self.attack["heighten"]["effect"], self.character, Target_Model
                    )
                    print(heighten_data)
        else:
            heighten = 0
        return (heighten_data, heighten)

    def heighten_calc(self, data, heighten, heighten_data):
        if heighten > 0:
            for i in heighten_data["dmg"].keys():
                sub_data = heighten_data["dmg"][i]["sub_data"]
                for die_size in sub_data.keys():
                    die_num = int(sub_data[die_size]) * heighten
                    heighten_roll = f"{die_num}d{die_size}"
                    try:
                        data["dmg"][i]["roll_string"] = f"{str(data['dmg'][i]['roll_string'])}+{heighten_roll}"
                    except KeyError:
                        data["dmg"][i]["roll_string"] = heighten_roll
        return data


class Attack_Data:
    def __init__(self, dmg_string, total_damage, success_string, attack_output_string):
        self.dmg_string = dmg_string
        self.total_damage = total_damage
        self.success_string = success_string
        self.output = attack_output_string

    def __str__(self):
        return self.output

    def __int__(self):
        return self.total_damage

    def __float__(self):
        return self.total_damage


# Spell Subclass
async def get_spell(character, attack_name, level, ctx, guild=None):
    print(attack_name)
    guild = await get_guild(ctx, guild)
    CharacterModel = await get_character(character, ctx, guild=guild, engine=engine)
    try:
        spell_data = await CharacterModel.get_spell(attack_name)
    except Exception:
        spell_data = ""
    return Spell(ctx, guild, CharacterModel, attack_name, spell_data, level)


class Spell(AutoModel):
    def __init__(self, ctx, guild, character: EPF_Character, attack_name: str, attack_data: dict, level: int):
        self.level = level
        super().__init__(ctx, guild, character, attack_name, attack_data)
        print(attack_data)
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
            self.attack_type = self.attack["type"]

    async def legacy_cast_attk_attk(self, Target_Model: EPF_Character, attack_modifier, target_modifier):
        attack_roll = d20.roll(
            f"1d20+{await self.character.get_spell_mod(self.attack_name, True)}{ParseModifiers(attack_modifier)}"
        )
        goal_result = d20.roll(f"{Target_Model.ac_total}{ParseModifiers(target_modifier)}")

        success_string = PF2_eval_succss(attack_roll, goal_result)
        attk_output_string = (
            f"{self.character.char_name} casts {self.attack_name} at"
            f" {Target_Model.char_name}:\n{attack_roll}\n{success_string}"
        )

        return Attack_Data(None, 0, success_string, attk_output_string)

    async def legacy_cast_attk_dmg(
        self, Target_Model: EPF_Character, success_string: str, dmg_modifier, dmg_type_override
    ):
        if success_string == "Critical Success" and "critical-hits" not in Target_Model.resistance.keys():
            dmg_string, total_damage = await legacy_roll_spell_dmg_resist(
                self.character,
                Target_Model,
                self.attack_name,
                self.level,
                True,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
            )

        elif success_string == "Success" or success_string == "Critical Success":
            dmg_string, total_damage = await legacy_roll_spell_dmg_resist(
                self.character,
                Target_Model,
                self.attack_name,
                self.level,
                False,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
            )

        else:
            dmg_string = None
            total_damage = 0

        return Attack_Data(dmg_string, total_damage, success_string, "")

    async def legacy_cast_save_attk(self, Target_Model: EPF_Character, attack_modifier, target_modifier):
        try:
            save_type = self.attack["save"]["value"]
        except TypeError:
            save_type = self.attack["save"]
        save_dc = d20.roll(
            f"{await self.character.get_spell_mod(self.attack_name, False)}{ParseModifiers(attack_modifier)}"
        )
        roll = d20.roll(f"{await Target_Model.get_roll(save_type.title())}{ParseModifiers(target_modifier)}")

        success_string = PF2_eval_succss(roll, save_dc)
        attk_output_string = (
            f"{self.character.char_name.title()} casts"
            f" {self.attack_name.title()}.\n{Target_Model.char_name.title()} makes a"
            f" {save_type.title()} save!\n{self.character.char_name} forced the save.\n{roll}\n{success_string}"
        )

        return Attack_Data(None, 0, success_string, attk_output_string)

    async def legacy_cast_save_dmg(
        self, Target_Model: EPF_Character, success_string: str, dmg_modifier, dmg_type_override
    ):
        if success_string == "Critical Failure":
            dmg_string, total_damage = await legacy_roll_spell_dmg_resist(
                self.character,
                Target_Model,
                self.attack_name,
                self.level,
                True,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
            )
        elif success_string == "Failure":
            dmg_string, total_damage = await legacy_roll_spell_dmg_resist(
                self.character,
                Target_Model,
                self.attack_name,
                self.level,
                False,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
            )
        elif success_string == "Success":
            dmg_string, total_damage = await legacy_roll_spell_dmg_resist(
                self.character,
                Target_Model,
                self.attack_name,
                self.level,
                False,
                flat_bonus=dmg_modifier,
                dmg_type_override=dmg_type_override,
                half=True,
            )
        else:
            dmg_string = None
            total_damage = 0

        return Attack_Data(dmg_string, total_damage, success_string, "")

    async def cast(self, target, attack_modifier, target_modifier, dmg_modifier, dmg_type_override):
        Target_Model = await get_EPF_Character(target, self.ctx, engine=engine, guild=self.guild)

        if self.complex:
            pass
        else:
            if self.attack_type == "attack":
                Attk_Data = await self.legacy_cast_attk_attk(Target_Model, attack_modifier, target_modifier)
                Dmg_Data = await self.legacy_cast_attk_dmg(
                    Target_Model, Attk_Data.success_string, dmg_modifier, dmg_type_override
                )

            elif self.attack_type == "save":
                Attk_Data = await self.legacy_cast_save_attk(Target_Model, attack_modifier, target_modifier)
                Dmg_Data = await self.legacy_cast_save_dmg(
                    Target_Model, Attk_Data.success_string, dmg_modifier, dmg_type_override
                )
            else:
                return None

        spell_data = Attack_Data(Dmg_Data.dmg_string, Dmg_Data.total_damage, Dmg_Data.success_string, Attk_Data.output)

        await self.format_output(spell_data, Target_Model)
        return self.output


attack_grammer = """
start: phrase+

phrase: value+ break

value: roll_string WORD                                                -> damage_string
    | persist_dmg
    | WORD NUMBER? (duration | unit | auto | stable | flex | target | data | self)*   -> new_condition
    | heighten_persist

persist_dmg : ("persistent dmg" | "pd") roll_string WORD* ["/" "dc" (NUMBER | STAT_VAR) save_string]
heighten_persist: "hpd" roll_string WORD


duration : "duration:" NUMBER
unit : "unit:" WORD
auto: "auto"
data: "data:" SINGLE_QUOTED_STRING
stable: "stable"
flex: "flex"
target: "myturn"
self: "self"

modifier: SIGNED_INT

quoted: SINGLE_QUOTED_STRING
    | DOUBLE_QUOTED_STRING

break: ","


roll_string: ROLL (POS_NEG ROLL)* (POS_NEG (NUMBER | STAT_VAR))*
!save_string: "reflex" | "fort" | "will" | "flat"

ROLL: NUMBER "d" NUMBER

POS_NEG : ("+" | "-")
STAT_VAR : ("str" | "dex" | "con" | "int" | "wis" | "cha" | "lvl" | "dc")

DOUBLE_QUOTED_STRING  : /"[^"]*"/
SINGLE_QUOTED_STRING  : /'[^']*'/

SPECIFIER : "c" | "s" | "i" | "r" | "w"
VARIABLE : "+x" | "-x" | POS_NEG? "lvl" | (POS_NEG?  ROLL)


COMBO_WORD : WORD ("-"|"_") WORD
%import common.ESCAPED_STRING
%import common.WORD
%import common.SIGNED_INT
%import common.NUMBER
%import common.WS
%ignore WS
"""


async def automation_parse(data, character_model, target_model):
    processed_data = {}
    try:
        if data[-1:] != ",":
            data = data + ","

        tree = Lark(attack_grammer).parse(data)
        # print(data)
        # print(tree.pretty())
        processed_data = await parse_automation_tree(tree, processed_data, character_model, target_model)
    except Exception:
        processed_input = data.split(",")
        for item in processed_input:
            try:
                if data[-1:] != ",":
                    data = data + ","

                tree = Lark(attack_grammer).parse(data)
                # print(tree.pretty())
                processed_data = await parse_automation_tree(tree, processed_data, character_model, target_model)
            except Exception as e:
                logging.error(f"Bad input: {item}: {e}")

    return processed_data


async def parse_automation_tree(tree, output_data: dict, char_model, target_model):
    t = tree.iter_subtrees_topdown()
    for branch in t:
        if branch.data == "new_condition":
            data = {"title": "", "number": 0}

            for item in branch.children:
                if type(item) == lark.Token:
                    if item.type == "WORD":
                        data["title"] = item.value
                    elif item.type == "NUMBER":
                        data["number"] = item.value
                elif type(item) == lark.Tree:
                    try:
                        data[str(item.data)] = item.children[0].value
                    except IndexError:
                        data[str(item.data)] = 0

            unit = "Round"
            if "unit" in data.keys():
                if data["unit"] in ["round", "minute", "hour", "days"]:
                    unit = data["unit"].title()

            auto = False
            if "auto" in data.keys():
                auto = True

            action = ""
            if "data" in data.keys():
                action = data_stat_var(data["data"], char_model)
                action = action.strip("'")

            if "duration" in data.keys():
                if int(data["duration"]) != int(data["number"]):
                    action = action + " " + f"stable {data['number']}"
                    data["number"] = data["duration"]

            if "stable" in data.keys():
                action = action + " " + f"stable {data['number']}"

            flex = False
            if "flex" in data.keys():
                flex = True

            target = None
            if "target" in data.keys():
                target = char_model.char_name

            if "self" in data.keys():
                data["char_name"] = char_model.char_name
            else:
                data["char_name"] = target_model.char_name

            # TODO Move this out to the main method
            if "self" in data.keys():
                if "target" in data.keys():
                    target = target_model.char_name

                if data["title"].title() not in await char_model.conditions():
                    await char_model.set_cc(
                        data["title"].title(),
                        False,
                        int(data["number"]),
                        unit,
                        auto,
                        flex=flex,
                        data=action,
                        target=target,
                    )
                    # print(action)
            else:
                if data["title"].title() not in await target_model.conditions():
                    await target_model.set_cc(
                        data["title"].title(),
                        False,
                        int(data["number"]),
                        unit,
                        auto,
                        flex=flex,
                        data=action,
                        target=target,
                    )
                    # print(action)

            output_data["condition"] = data

        elif branch.data == "persist_dmg":
            # TODO Address variables
            temp = {}
            for item in branch.children:
                if type(item) == lark.Tree:
                    if item.data == "roll_string":
                        roll_string = ""
                        for sub in item.children:
                            var = stat_var(sub, char_model)
                            if sub is not None:
                                roll_string = roll_string + var

                        temp["roll_string"] = roll_string
                    elif item.data == "save_string":
                        for sub in item.children:
                            temp["save"] = sub.value
                elif type(item) == lark.Token:
                    if item.type == "WORD":
                        temp["dmg_type"] = item.value
                    elif item.type == "NUMBER":
                        temp["save_value"] = item.value
                    elif item.type == "STAT_VAR":
                        var = stat_var(item, char_model)
                        temp["save_value"] = var
            output_data["pd"] = temp

        elif branch.data == "heighten_persist":
            temp = {}
            for item in branch.children:
                if type(item) == lark.Tree:
                    if item.data == "roll_string":
                        roll_string = ""
                        for sub in item.children:
                            if sub is not None:
                                var = stat_var(sub, char_model)
                                if sub is not None:
                                    roll_string = roll_string + var

                        temp["roll_string"] = roll_string
                elif type(item) == lark.Token:
                    if item.type == "WORD":
                        temp["dmg_type"] = item.value
            output_data["hpd"] = temp

        elif branch.data == "damage_string":
            if "dmg" not in output_data.keys():
                output_data["dmg"] = {}

            temp = {}
            for item in branch.children:
                # print(item)

                if type(item) == lark.Tree:
                    if item.data == "roll_string":
                        roll_string = ""
                        sub_data = None
                        for sub in item.children:
                            sub_data = {}
                            # print(sub.value)
                            # print(sub.type)
                            if sub.type == "ROLL":
                                sub_list = sub.value.split("d")
                                sub_data[sub_list[1]] = sub_list[0]

                            if sub is not None:
                                var = stat_var(sub, char_model)
                                if sub is not None:
                                    roll_string = roll_string + var

                        temp["roll_string"] = roll_string
                elif type(item) == lark.Token:
                    if item.type == "WORD":
                        temp["dmg_type"] = item.value

            if temp["dmg_type"] is not None and temp["roll_string"] is not None:
                output_data["dmg"][temp["dmg_type"]] = {"roll_string": temp["roll_string"]}
                try:
                    output_data["dmg"][temp["dmg_type"]]["sub_data"] = sub_data
                except Exception:
                    pass

    return output_data


async def scripted_damage_roll_resists(
    data: dict, Target_Model, crit: bool, flat_bonus="", dmg_type_override=None, half=False
):
    dmg_output = []
    total_damage = 0
    try:
        for x, key in enumerate(data["dmg"]):
            try:
                dmg_string = (
                    f"({data['dmg'][key]['roll_string']}{ParseModifiers(flat_bonus) if x == 0 else ''})"
                    f"{'*2' if crit else ''}{'/2' if half else ''}"
                )
            except KeyError:
                dmg_string = (
                    f"({data['dmg'][key]}{ParseModifiers(flat_bonus) if x == 0 else ''})"
                    f"{'*2' if crit else ''}{'/2' if half else ''}"
                )
            damage_roll = d20.roll(dmg_string)

            if dmg_type_override == "":
                dmg_type_override = None
            if dmg_type_override is not None:
                base_dmg_type = dmg_type_override
            else:
                base_dmg_type = key
            total_damage += await damage_calc_resist(damage_roll.total, base_dmg_type, Target_Model)
            dmg_output_string = f"{damage_roll}"
            output = {"dmg_output_string": dmg_output_string, "dmg_type": base_dmg_type}
            dmg_output.append(output)

        try:
            total_damage = total_damage - Target_Model.character_model.bonuses["other"]["hardness"]
        except KeyError:
            pass
    except KeyError:
        pass
    print(dmg_output)

    return dmg_output, total_damage


async def legacy_roll_spell_dmg_resist(
    Character_Model: EPF_Character,
    Target_Model: EPF_Character,
    spell: str,
    level: int,
    crit: bool,
    flat_bonus="",
    dmg_type_override=None,
    half=False,
):
    """
    Rolls damage and calculates resists
    :param Character_Model:
    :param Target_Model:
    :param attack:
    :param crit:
    :return: Tuple of damage_output_string(string), total_damage(int)
    """
    logging.info("roll_dmg_spell_resist")
    # Roll the critical damage and apply resistances
    dmg_rolls = {}
    # print(spell, crit)
    if crit and "critical-hits" not in Target_Model.resistance.keys():
        spell_dmg = await Character_Model.get_spell_dmg(spell, level, flat_bonus=flat_bonus)
        # print(spell_dmg)
        for key in spell_dmg.keys():
            if dmg_type_override is not None:
                dmg_type = dmg_type_override
            else:
                dmg_type = spell_dmg[key]["dmg_type"]

            dmg_rolls[key] = {}
            dmg_rolls[key]["damage_string"] = spell_dmg[key]["dmg_string"]
            dmg_rolls[key]["damage_roll"] = d20.roll(f"({dmg_rolls[key]['damage_string']})*2")
            dmg_rolls[key]["damage_type"] = dmg_type
    else:
        spell_dmg = await Character_Model.get_spell_dmg(spell, level, flat_bonus=flat_bonus)
        # print(spell_dmg)

        for key in spell_dmg.keys():
            if dmg_type_override is not None:
                dmg_type = dmg_type_override
            else:
                dmg_type = spell_dmg[key]["dmg_type"]

            dmg_rolls[key] = {}
            dmg_rolls[key]["damage_string"] = spell_dmg[key]["dmg_string"]
            print(dmg_rolls[key])
            if half:
                dmg_rolls[key]["damage_roll"] = d20.roll(f"({dmg_rolls[key]['damage_string']})/2")
            else:
                dmg_rolls[key]["damage_roll"] = d20.roll(f"{dmg_rolls[key]['damage_string']}")
            dmg_rolls[key]["damage_type"] = dmg_type

    total_damage = 0
    for key in spell_dmg.keys():
        total_damage += await damage_calc_resist(
            dmg_rolls[key]["damage_roll"].total, dmg_rolls[key]["damage_type"], Target_Model
        )

    # Convert to standard format
    dmg_output = []
    for key in dmg_rolls:
        convert = {"dmg_output_string": dmg_rolls[key]["damage_roll"], "dmg_type": dmg_rolls[key]["damage_type"]}
        dmg_output.append(convert)

    # print(dmg_output_string, total_damage)
    print(dmg_output)
    return dmg_output, total_damage


def stat_var(item: lark.Token, char_model: EPF_Character):
    match item.value:  # noqa
        case "str":
            var = char_model.str_mod
        case "dex":
            var = char_model.dex_mod
        case "con":
            var = char_model.con_mod
        case "int":
            var = char_model.itl_mod
        case "wis":
            var = char_model.wis_mod
        case "cha":
            var = char_model.cha_mod
        case "lvl":
            var = char_model.character_model.level
        case "dc":
            var = char_model.class_dc
        case _:
            var = item.value
    return var


def data_stat_var(string: str, char_model: EPF_Character):
    if "_str_" in string:
        string = string.replace("_str", str(char_model.str_mod))
    if "_dex_" in string:
        string = string.replace("_dex_", str(char_model.dex_mod))
    if "_con_" in string:
        string = string.replace("_con_", str(char_model.con_mod))
    if "_int_" in string:
        string = string.replace("_int_", str(char_model.itl_mod))
    if "_wis_" in string:
        string = string.replace("_wis_", str(char_model.wis_mod))
    if "_cha_" in string:
        string = string.replace("_cha_", str(char_model.cha_mod))
    if "_lvl_" in string:
        string = string.replace("_lvl_", str(char_model.character_model.level))
    if "_dc_" in string:
        string = string.replace("_dc_", str(char_model.class_dc))

    return string
