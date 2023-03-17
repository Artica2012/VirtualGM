import logging

import d20
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from Base.Automation import Automation
from EPF.EPF_Character import get_EPF_Character
from PF2e.pf2_functions import PF2_eval_succss
from error_handling_reporting import error_not_initialized
from utils.Char_Getter import get_character
from utils.Tracker_Getter import get_tracker_model
from utils.parsing import ParseModifiers


class EPF_Automation(Automation):
    def __init__(self, ctx, engine, guild):
        super().__init__(ctx, engine, guild)

    async def attack(self, character, target, roll, vs, attack_modifier, target_modifier):
        try:
            # if type(roll[0]) == int:
            roll_string: str = f"{roll}{ParseModifiers(attack_modifier)}"
            # print(roll_string)
            dice_result = d20.roll(roll_string)
        except:
            char_model = await get_character(character, self.ctx, guild=self.guild, engine=self.engine)
            # print(await char_model.get_roll(roll))
            roll_string = f"({await char_model.get_roll(roll)}){ParseModifiers(attack_modifier)}"
            # print(roll_string)
            dice_result = d20.roll(roll_string)

        opponent = await get_character(target, self.ctx, guild=self.guild, engine=self.engine)
        goal_value = await opponent.get_dc(vs)

        try:
            goal_string: str = f"{goal_value}{ParseModifiers(target_modifier)}"
            goal_result = d20.roll(goal_string)
        except Exception as e:
            logging.warning(f"attack: {e}")
            return "Error"

        # Format output string
        success_string = PF2_eval_succss(dice_result, goal_result)
        output_string = f"{character} vs {target} {vs} {target_modifier}:\n{dice_result}\n{success_string}"
        return output_string

    async def save(self, character, target, save, dc, modifier):
        if target is None:
            output_string = "Error. No Target Specified."
            return output_string
        print(f" {save}, {dc}, {modifier}")
        async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        attacker = await get_EPF_Character(character, self.ctx, guild=self.guild, engine=self.engine)
        opponent = await get_EPF_Character(target, self.ctx, guild=self.guild, engine=self.engine)

        orig_dc = dc

        if dc is None:
            dc = await attacker.get_dc("DC")
            print(dc)
        try:
            print(await opponent.get_roll(save))
            dice_result = d20.roll(f"{await opponent.get_roll(save)}{ParseModifiers(modifier)}")
            print(dice_result)
            # goal_string: str = f"{dc}"
            goal_result = d20.roll(f"{dc}")
            print(goal_result)
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False
        try:
            success_string = PF2_eval_succss(dice_result, goal_result)
            print(success_string)
            # Format output string
            if character == target:
                output_string = f"{character} makes a {save} save!\n{dice_result}\n{success_string if orig_dc else ''}"
            else:
                output_string = (
                    f"{target} makes a {save} save!\n{character} forced the save.\n{dice_result}\n{success_string}"
                )

        except NoResultFound:
            await self.ctx.channel.send(error_not_initialized, delete_after=30)
            return False
        except Exception as e:
            logging.warning(f"attack: {e}")
            return False

        return output_string

    async def damage(self, bot, character, target, roll, modifier, healing, crit=False):
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)
        try:
            roll_result: d20.RollResult = d20.roll(f"({roll}){ParseModifiers(modifier)}")
        except Exception:
            try:
                roll_result = d20.roll(f"({Character_Model.weapon_dmg(roll)}){ParseModifiers(modifier)}")
            except:
                try:
                    roll_result = d20.roll(f"{Character_Model.get_roll(roll)}{ParseModifiers(modifier)}")
                except:
                    roll_result = d20.roll("0 [Error]")

        output_string = f"{character} {'heals' if healing else 'damages'}  {target} for: \n{roll_result}"
        await Target_Model.change_hp(roll_result.total, healing)
        await Tracker_Model.update_pinned_tracker()
        return output_string

    async def auto(self, bot, character, target, attack):
        Tracker_Model = await get_tracker_model(self.ctx, bot, engine=self.engine, guild=self.guild)
        Character_Model = await get_character(character, self.ctx, engine=self.engine, guild=self.guild)
        Target_Model = await get_character(target, self.ctx, engine=self.engine, guild=self.guild)

        # Attack
        roll_string = f"({await Character_Model.get_roll(attack)})"
        print(roll_string)
        dice_result = d20.roll(roll_string)

        goal_value = Target_Model.ac_total
        print(goal_value)
        try:
            goal_string: str = f"{goal_value}"
            print(goal_string)
            goal_result = d20.roll(goal_string)
            print(goal_result)
        except Exception as e:
            logging.warning(f"auto: {e}")
            return "Error"

        # Format output string

        success_string = PF2_eval_succss(dice_result, goal_result)
        print(success_string)
        attk_output_string = f"{character} vs {target}:\n{dice_result}\n{success_string}"
        print(attk_output_string)

        # Damage
        if success_string == "Critical Success":
            dmg_output_string = await Character_Model.weapon_dmg(attack, crit=True)
            print(dmg_output_string)
        elif success_string == "Success":
            dmg_output_string = await Character_Model.weapon_dmg(attack)
            print(dmg_output_string)
        else:
            dmg_output_string = None

        if dmg_output_string is not None:
            dmg_roll = d20.roll(dmg_output_string)
            dmg_output_string = f"{character} damages {target} for:\n{dmg_roll}"
            await Target_Model.change_hp(dmg_roll.total, heal=False, post=False)
            if Target_Model.player:
                return f"{attk_output_string}\n{dmg_output_string}\n{Target_Model.char_name} damaged for {dmg_roll.total}.New HP: {Target_Model.current_hp}/{Target_Model.max_hp}"
            else:
                return f"{attk_output_string}\n{dmg_output_string}\n{Target_Model.char_name} damaged for {dmg_roll.total}. {await Target_Model.calculate_hp()}"
        else:
            return attk_output_string















