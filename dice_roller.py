# dice roller
# dice roller module

# imports
import random
import re

# Dice Roller Class
class DiceRoller:
    def __init__(self, input_string: str):
        self.input_string = input_string

    # rolls the dice in an XdY format
    def roller(self, input: str):
        dice = input.split('d')
        num_die = int(dice[0])
        size_die = int(dice[1])
        # print(f"num_die = {num_die}, size_die = {size_die}")
        results = []
        for die in range(num_die):
            roll = random.randint(1, size_die)
            results.append(roll)
        # print(results)
        return results

    # Parses out the Roll from the Text in the format of Roll (space) Text
    def _text_parse(self, input: str):
        text_parse = input.split(' ', 1)
        # print(text_parse)
        dice_string = text_parse[0]
        try:
            text = text_parse[1]
        except:
            text = 'Roll'
        return dice_string, text

    # Parses out each individaul dice roll with addition or subtraction signs
    def _dice_parse(self, input: str):
        dice_string = input.strip()
        dice_string = dice_string.lower()
        parsed_dice = re.split(r'([+,-])', dice_string)
        # print(f'Parsed Dice: {parsed_dice}')
        for x, item in enumerate(parsed_dice):
            # print(f"{item}, {x}")
            if "d" in item:
                parsed_dice[x] = self.roller(item)
        return parsed_dice

    # Does the additioin and subtraction between the dice rolls
    def _math_equation(self, equation: list):
        total = 0
        add = True
        for item in equation:
            if type(item) is list:
                total += sum(item)
            if type(item) is  str:
                if item == '+':
                    add = True
                elif item == '-':
                    add = False
                else:
                    if add:
                        total += int(item)
                    else:
                        total -= int(item)
        return total
    # formats the output
    def _format_output(self, text: str, dice, total):
        dice_string = ""
        dice_string = ' '.join(map(str, dice))
        return f'{text}: {dice_string} = **{total}**'
    # the
    def roll_dice(self):
        parsed_text = self._text_parse(self.input_string)
        parsed_dice = self._dice_parse(parsed_text[0])
        calculated_total = self._math_equation(parsed_dice)
        return self._format_output(parsed_text[1], parsed_dice, calculated_total)

    def plain_roll(self, dice: str):
        parsed_dice = self._dice_parse(dice)
        calculated_total = self._math_equation(parsed_dice)
        return parsed_dice, calculated_total
