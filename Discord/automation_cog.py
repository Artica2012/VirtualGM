# automation_cog.py

import logging

# imports
import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands

from Backend.Database.database_operations import log_roll
from Backend.utils.Automation_Getter import get_automation
from Backend.utils.Tracker_Getter import get_tracker_model
from Backend.utils.error_handling_reporting import ErrorReport
from Backend.utils.utils import get_guild
from Discord.auto_complete import (
    character_select_gm,
    a_macro_select,
    a_d_macro_select,
    get_attributes,
    save_select,
    spell_list,
    spell_level,
    var_dmg_type,
    auto_macro_select,
    a_save_target_custom_multi,
    character_select_multi,
    dmg_type,
)


class AutomationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ---------------------------------------------------

    # ---------------------------------------------------
    # Slash commands

    att = SlashCommandGroup("a", "Automatic Attack Commands")

    @att.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select_multi)
    @option("roll", description="Roll or Macro Roll", autocomplete=a_macro_select)
    @option("vs", description="Target Attribute", autocomplete=get_attributes)
    @option("attack_modifier", description="Modifier to the macro (defaults to +)", required=False)
    @option("target_modifier", description="Modifier to the target's dc (defaults to +)", required=False)
    async def attack(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        roll: str,
        vs: str,
        attack_modifier: str = "",
        target_modifier: str = "",
    ):
        logging.info("attack_cog attack")
        guild = await get_guild(ctx, None)
        try:
            await ctx.response.defer()
            Automation = await get_automation(ctx, guild=guild)
            embeds = []
            if "," in target:
                multi_target = target.split(",")
                for char in multi_target:
                    try:
                        data = await Automation.attack(
                            character, char.strip(), roll, vs, attack_modifier, target_modifier, multi=True
                        )
                        embeds.append(data.embed)

                    except Exception:
                        embeds.append(
                            discord.Embed(title=char, fields=[discord.EmbedField(name=roll, value="Invalid Target")])
                        )
                Tracker_Model = await get_tracker_model(ctx)
                await Tracker_Model.update_pinned_tracker()
            else:
                data = await Automation.attack(character, target, roll, vs, attack_modifier, target_modifier)
                embeds.append(data.embed)
            await ctx.send_followup(embeds=embeds)

            # print("Logging")
            for item in embeds:
                log_output = f"{roll}:\n{item.fields[0].value}"
                await log_roll(guild.id, character, log_output)
        except AttributeError:
            await ctx.send_followup("Error. Ensure that you selected valid targets and attributes.")
        except Exception as e:
            logging.warning(f"attack_cog attack {e}")
            report = ErrorReport(ctx, "/a attack", e, self.bot)
            await report.report()
            await ctx.send_followup(
                "Error. Ensure that you selected valid targets and attack rolls.  Ensure that if "
                "you used a non-macro roll that it conforms to the XdY+Z format without any "
                "labels."
            )

    @att.command(description="Saving Throw")
    @option("character", description="Character forcing the save", autocomplete=character_select_gm)
    @option("target", description="Saving Character", autocomplete=a_save_target_custom_multi)
    @option("save", description="Save", autocomplete=save_select)
    @option("modifier", description="Modifier to the macro (defaults to +)", required=False)
    async def save(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        save: str,
        dc: int = None,
        modifier: str = "",
    ):
        logging.info("attack_cog save")
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        try:
            Automation = await get_automation(ctx, guild=guild)
            embeds = []
            if "," in target:
                multi_target = target.split(",")
                for char in multi_target:
                    try:
                        data = await Automation.save(character, char.strip(), save, dc, modifier)
                        embeds.append(data.embed)
                    except Exception:
                        embeds.append(
                            discord.Embed(title=char, fields=[discord.EmbedField(name=save, value="Invalid Target")])
                        )
            else:
                data = await Automation.save(character, target, save, dc, modifier)
                embeds.append(data.embed)
            await ctx.send_followup(embeds=embeds)
            # print("Logging")
            for item in embeds:
                log_output = f"{save}:\n{item.fields[0].value}"
                await log_roll(guild.id, character, log_output)

        except Exception as e:
            logging.warning(f"attack_cog save {e}")
            report = ErrorReport(ctx, "/a save", e, self.bot)
            await report.report()
            await ctx.send_followup("Error. Ensure that you selected valid targets and saves.")

    @att.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select_multi)
    @option("user_roll_str", description="Roll or Macro Roll", autocomplete=a_d_macro_select)
    @option("modifier", description="Roll Modifier", default="", type=str)
    @option("healing", description="Apply as Healing?", default=False, type=bool)
    @option("damage_type", description="Damage Type", autocomplete=var_dmg_type, required=False)
    @option("crit", description="Critical Hit", choices=[True, False])
    async def damage(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        user_roll_str: str,
        modifier: str = "",
        healing: bool = False,
        damage_type: str = "",
        crit: bool = False,
    ):
        logging.info("attack_cog damage")
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        try:
            Automation = await get_automation(ctx, guild=guild)
            embeds = []
            if "," in target:
                multi_target = target.split(",")
                for char in multi_target:
                    try:
                        data = await Automation.damage(
                            self.bot,
                            character,
                            char.strip(),
                            user_roll_str,
                            modifier,
                            healing,
                            damage_type,
                            multi=True,
                            crit=crit,
                        )
                        embeds.append(data.embed)
                    except Exception:
                        embeds.append(
                            discord.Embed(
                                title=char, fields=[discord.EmbedField(name=user_roll_str, value="Invalid Target")]
                            )
                        )

            else:
                data = await Automation.damage(
                    self.bot, character, target, user_roll_str, modifier, healing, damage_type, crit=crit
                )

                embeds.append(data.embed)
            await ctx.send_followup(embeds=embeds)

            Tracker_Model = await get_tracker_model(ctx)
            await Tracker_Model.update_pinned_tracker()
            # print("Logging")
            for item in embeds:
                log_output = f"{user_roll_str}:\n{item.fields[0].value}"
                await log_roll(guild.id, character, log_output)

        except Exception as e:
            logging.warning(f"attack_cog damage {e}")
            report = ErrorReport(ctx, "/a damage", e, self.bot)
            await report.report()
            await ctx.send_followup("Error. Ensure that your input was a valid dice roll or value.")

    @att.command(description="Automatic Attack")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select_multi)
    @option("attack", description="Roll or Macro Roll", autocomplete=auto_macro_select)
    @option("attack_modifier", description="Attack Modifier", required=False)
    @option("target_modifier", description="Target Modifier", required=False)
    @option("damage_modifier", description="Flat Bonus or Penalty to Damage", required=False)
    @option("damage_type_override", description="Override the base damage type", autocomplete=dmg_type, required=False)
    async def auto(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        attack: str,
        attack_modifer: str = "",
        target_modifier: str = "",
        damage_modifier: str = "",
        damage_type_override: str = None,
    ):
        logging.info("attack_cog auto")
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        try:
            Automation = await get_automation(ctx)
            embeds = []
            if "," in target:
                multi_target = target.split(",")
                for char in multi_target:
                    try:
                        data = await Automation.auto(
                            self.bot,
                            character,
                            char.strip(),
                            attack,
                            attack_modifer,
                            target_modifier,
                            damage_modifier,
                            damage_type_override,
                            multi=True,
                        )
                        embeds.append(data.embed)
                    except Exception:
                        embeds.append(
                            discord.Embed(title=char, fields=[discord.EmbedField(name=attack, value="Invalid Target")])
                        )

            else:
                data = await Automation.auto(
                    self.bot,
                    character,
                    target,
                    attack,
                    attack_modifer,
                    target_modifier,
                    damage_modifier,
                    damage_type_override,
                )
                embeds.append(data.embed)
            await ctx.send_followup(embeds=embeds)
            Tracker_Model = await get_tracker_model(ctx)
            await Tracker_Model.update_pinned_tracker()
            # print("Logging")
            for item in embeds:
                log_output = f"{attack}:\n{item.fields[0].value}"
                await log_roll(guild.id, character, log_output)

        except KeyError:
            await ctx.send_followup("Error. Ensure that you have selected a valid attack.")
        except Exception as e:
            logging.warning(f"attack_cog auto {e}")
            report = ErrorReport(ctx, "/a auto", e, self.bot)
            await report.report()
            await ctx.send_followup("Error. Ensure that you selected a valid target and attack.")

    @att.command(description="Cast a Spell (EPF Only)")
    @option("character", description="Character Attacking", autocomplete=character_select_gm)
    @option("target", description="Character to Target", autocomplete=character_select_multi)
    @option("spell", description="Roll or Macro Roll", autocomplete=spell_list)
    @option("level", description="Spell Level", autocomplete=spell_level)
    @option("attack_modifier", description="Attack Modifier", required=False)
    @option("target_modifier", description="Target Modifier", required=False)
    @option("damage_modifier", description="Flat Bonus or Penalty to Damage", required=False)
    @option("damage_type_override", description="Override the base damage type", autocomplete=dmg_type, required=False)
    async def cast(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        target: str,
        spell: str,
        level: int,
        attack_modifer: str = "",
        target_modifier: str = "",
        damage_modifier: str = "",
        damage_type_override: str = None,
    ):
        logging.info("attack_cog cast")
        await ctx.response.defer()
        guild = await get_guild(ctx, None)
        try:
            Automation = await get_automation(ctx, guild=guild)
            embeds = []
            if "," in target:
                multi_target = target.split(",")
                for char in multi_target:
                    try:
                        data = await Automation.cast(
                            self.bot,
                            character,
                            char.strip(),
                            spell,
                            level,
                            attack_modifer,
                            target_modifier,
                            damage_modifier,
                            damage_type_override,
                            multi=True,
                        )
                        embeds.append(data.embed)

                    except Exception:
                        embeds.append(
                            discord.Embed(title=char, fields=[discord.EmbedField(name=spell, value="Invalid Target")])
                        )

            else:
                data = await Automation.cast(
                    self.bot,
                    character,
                    target,
                    spell,
                    level,
                    attack_modifer,
                    target_modifier,
                    damage_modifier,
                    damage_type_override,
                )

                embeds.append(data.embed)
            await ctx.send_followup(embeds=embeds)
            Tracker_Model = await get_tracker_model(ctx)
            await Tracker_Model.update_pinned_tracker()

            print("Logging")
            for item in embeds:
                log_output = f"{spell}:\n{item.fields[0].value}"
                await log_roll(guild.id, character, log_output)

        except Exception as e:
            logging.warning(f"attack_cog cast {e}")
            report = ErrorReport(ctx, "/a cast", e, self.bot)
            await report.report()
            await ctx.send_followup("Error.  Ensure that you selected a valid spell, target and level.")


def setup(bot):
    bot.add_cog(AutomationCog(bot))
