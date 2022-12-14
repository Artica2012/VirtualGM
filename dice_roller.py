# dice_roller.py
# dice roller module

# imports
import asyncio
import datetime
import random
import re
import inspect

# Logging
import logging

# Dice Roller Class
class DiceRoller:
    def __init__(self, input_string: str):
        self.input_string = input_string

    # rolls the dice in an XdY format
    async def roller(self, input_string: str):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller roller")

        dice = input_string.split('d')
        num_die = int(dice[0])
        size_die = int(dice[1])
        # print(f"num_die = {num_die}, size_die = {size_die}")
        results = []
        for die in range(num_die):
            await asyncio.sleep(0)
            roll = random.randint(1, size_die)
            results.append(roll)
        # print(results)
        return results

    # Parses out multiple rolls separated by a comma
    async def multi_roll_parse(self, input_string: str):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller multi_roll_parse")


        original_list = input_string.split(',')
        roll_list = []
        for item in original_list:
            await asyncio.sleep(0)
            # print(item)
            roll_list.append(item.strip())

        return roll_list

    # Parses out the Roll from the Text in the format of Roll (space) Text
    async def _text_parse(self, input_string: str):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller -_text_parse_")

        text_parse = input_string.split(' ', 1)
        # print(text_parse)
        dice_string = text_parse[0]
        try:
            text = text_parse[1]
        except:
            text = 'Roll'
        return dice_string, text

    # Parses out each individual dice roll with addition or subtraction signs
    async def _dice_parse(self, input_string: str):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller _dice_parse")

        dice_string = input_string.strip()
        dice_string = dice_string.lower()
        parsed_dice = re.split(r'([+,-])', dice_string)
        # print(f'Parsed Dice: {parsed_dice}')
        for x, item in enumerate(parsed_dice):
            await asyncio.sleep(0)
            # print(f"{item}, {x}")
            if "d" in item:
                parsed_dice[x] = await self.roller(item)
        return parsed_dice

    # Does the addition and subtraction between the dice rolls
    async def _math_equation(self, equation: list):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller _math_equation")


        total = 0  # Set the initial total to zero
        add = True  # Default it to add
        for item in equation:
            await asyncio.sleep(0)
            if type(item) is str:  # If its a string it should be either a +/- or a number
                if item == '+':
                    add = True
                elif item == '-':
                    add = False
                else:
                    if add:
                        total += int(item)
                    else:  # subtract it if the previous operator was a -
                        total -= int(item)
                        add = True  # once you subtract, reset the add variable to true
            # Hand the lists (set of die) separately since they need to be summed
            if type(item) is list:
                if add:
                    total += sum(item)
                else:
                    total -= sum(item)
                    add = True

        return total

    # formats the output
    async def _format_output(self, text: str, dice, total):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller _format_output")

        dice_string = ""
        dice_string = ' '.join(map(str, dice))
        return f'{text}: {dice_string} = **{total}**'

    ####
    # System Specific Code:

    async def _pf2_smart_dice_parse(self, input_string: str):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller _pf2_smart_dice_parse")


        crit_s = False
        crit_f = False
        dice_string = input_string.strip()
        dice_string = dice_string.lower()
        parsed_dice = re.split(r'([+,-])', dice_string)
        # print(f'Parsed Dice: {parsed_dice}')
        for x, item in enumerate(parsed_dice):
            await asyncio.sleep(0)
            # print(f"{item}, {x}")
            if "d" in item:
                roll = await self._pf2_smart_roller(item)
                parsed_dice[x] = roll[0]
                if roll[1] == True:
                    crit_s = True
                if roll[2] == True:
                    crit_f = True
        return parsed_dice, crit_s, crit_f

    async def _pf2_smart_roller(self, input_string: str):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller _pf2_smart_roller")


        crit_s = False
        crit_f = False
        dice = input_string.split('d')
        num_die = int(dice[0])
        size_die = int(dice[1])
        # print(f"num_die = {num_die}, size_die = {size_die}")
        results = []
        for die in range(num_die):
            await asyncio.sleep(0)
            roll = random.randint(1, size_die)
            results.append(roll)
            if roll == size_die and size_die == 20:
                crit_s = True
            elif roll == 1 and size_die == 20:
                crit_f = True
        # print(results)
        # print(results, crit_s, crit_f)
        return results, crit_s, crit_f

    ############################################################
    ############################################################
    # Exposed Methods

    async def roll_dice(self):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller roll_dice")



        # print('parsing Text')
        roll_list = await self.multi_roll_parse(self.input_string)
        # print(roll_list)
        output_string = ''
        for row in roll_list:
            await asyncio.sleep(0)
            parsed_text = await self._text_parse(row)
            # print(parsed_text)
            # print('Parsing Dice')
            parsed_dice = await self._dice_parse(parsed_text[0])
            # print(parsed_dice)
            # print('Doing math')
            calculated_total = await self._math_equation(parsed_dice)
            # print(calculated_total)
            output_string += f"{await self._format_output(parsed_text[1], parsed_dice, calculated_total)}\n"
            # print(output_string)
        return output_string

    async def attack_roll(self, dice: str):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller attack_roll")


        parsed_dice = await self._pf2_smart_dice_parse(dice)
        calculated_total = await self._math_equation(parsed_dice[0])
        dice_string = ""
        dice_string = ' '.join(map(str, parsed_dice[0]))
        # print(dice_string)
        return dice_string, calculated_total, parsed_dice[1], parsed_dice[2]

    async def plain_roll(self, dice: str):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller plain_roll")


        parsed_dice = await self._dice_parse(dice)
        calculated_total = await self._math_equation(parsed_dice)
        dice_string = ""
        dice_string = ' '.join(map(str, parsed_dice))
        return dice_string, calculated_total

    async def opposed_roll(self, dc: int):
        #bughunt code
        logging.info(f"{datetime.datetime.now()} - DiceRoller opposed_roll")


        # print('parsing Text')
        parsed_text = await self._text_parse(self.input_string)
        # print('Parsing Dice')
        parsed_dice = await self._dice_parse(parsed_text[0])
        # print('Doing math')
        calculated_total = await self._math_equation(parsed_dice)
        if calculated_total >= dc:
            dice_string = ""
            dice_string = ' '.join(map(str, parsed_dice))
            return f':thumbsup: {parsed_text[1]}: {dice_string} = **{calculated_total}** >= {dc}'
        else:
            dice_string = ""
            dice_string = ' '.join(map(str, parsed_dice))
            return f':thumbsdown: {parsed_text[1]}: {dice_string} = **{calculated_total}** >= {dc}'
