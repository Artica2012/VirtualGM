# help_cog.py

# imports
import discord
from discord.ext import commands
from discord import option
from discord.commands import SlashCommandGroup

import os
from dotenv import load_dotenv
import database_operations

# define global variables
load_dotenv(verbose=True)
if os.environ['PRODUCTION'] == 'True':
    TOKEN = os.getenv('TOKEN')
else:
    TOKEN = os.getenv('BETA_TOKEN')

GUILD = os.getenv('GUILD')
SERVER_DATA = os.getenv('SERVERDATA')


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    help = SlashCommandGroup("help", "Help Commands")

    @help.command(description='Setup Help',
                  # guild_ids=[GUILD]
                  )
    async def setup(self, ctx: discord.ApplicationContext):
        await ctx.respond("``` Setup \n"
                          "- To set up the bot, simply run the /i admin command and choose 'setup'.\n"
                          "- Once this is done, you should select a channel to be your main dice rolling channel and "
                          "run the /i admin command and choose 'tracker'.  This will pin  a tracker into the channel "
                          "for your player's usage.\n"
                          "- Next select a channel for the GM screen. This channel should ideally be hidden from the "
                          "players but VirtualGM will "
                          "need message permissions for the channel. Run the /i admin command and select 'gm "
                          "tracker'.  This channel will show a more verbose tracker, and will receive secret rolls.```",
                          ephemeral=True)

    @help.command(description="Roller",
                  # guild_ids=[GUILD]
                  )
    async def roller(self, ctx: discord.ApplicationContext):
        await ctx.respond("```"
                          " Dice Roller\n"
                          "- Dice are rolled with the /r slash command.\n"
                          "- The format is XdY+Z Label (e.g 1d20+7 Initiative)\n"
                          "- The dice roller will accept complex strings of dice (e.g 2d8+3d6-1d4+2)\n"
                          "- The optional secret command with the dice roller will send the result to the GM channel if it has been set up.\n"
                          "```", ephemeral=True
                          )

    @help.command(description="Initiative",
                  # guild_ids=[GUILD]
                  )
    @option('command', choices=[
        'admin', 'add', 'manage', 'next', 'init', 'hp', 'cc', 'cc_edit', 'cc_show'
    ])
    async def initiative(self, ctx: discord.ApplicationContext, command: str):
        if command == 'admin':
            await ctx.respond("```"
                              "admin - Administrative Commands (GM Restricted)\n"
                              "  - setup - Initializes the bot\n"
                              "  - transfer gm - Transfers the GM permissions to another user\n"
                              "  - tracker - posts a pinned tracker into the given channel and assigns it as the "
                              "active channel. This will deactivate the previous pinned tracker, (although it will not "
                              "delete nor unpin it, the old pin will just cease to update automatically)\n "
                              "  - gm tracker - posts a pinned gm tracker, which is more verbose and displays NPC hp "
                              "and counters. It will also assign the channel to act as the GM channel, which will "
                              "receive secret rolls.\n "
                              "```", ephemeral=True)
        elif command == 'add':
            await ctx.respond("```"
                              "add - Add a PC or NPC\n"
                              "- takes the argument player with the choice of player or NPC. NPCs have their health "
                              "obscured and do not show custom counters on the non-gm tracker. "
                              "```", ephemeral=True)
        elif command == 'manage':
            await ctx.respond("```"
                              "manage - Mange Initiative (GM Restricted)\n"
                              "  - start - Starts Initiative\n"
                              "  - stop - Stops Initiative\n"
                              "  - delete character - takes the argument character and will delete the character out of"
                              " the tracker. Will not function if it is currently the character's turn.\n"
                              "```", ephemeral=True)
        elif command == 'next':
            await ctx.respond("```"
                              "next - Advance Initiative"
                              "```", ephemeral=True)
        elif command == 'init':
            await ctx.respond("```"
                              "init - Assign an initiative value to the character\n"
                              "  - Takes the arguments character which is the character's name and initiative which can be given as a whole numner (e.g. 15) or a dice expression in the form of XdY+Z (e.g 1d20+7)"
                              "```", ephemeral=True)
        elif command == 'hp':
            await ctx.respond("```"
                              "hp - Adjust HP\n"
                              "  - Damage - Damages the indicated character for inputted amount\n"
                              "  - Heal - Heals the character for the inputted amount\n"
                              "  - Temporary HP - Grants the character the inputted amount of temporary HP. This HP will be subtracted from first and not added to with any healing."
                              "```", ephemeral=True)
        elif command == 'cc':
            await ctx.respond("```"
                              "cc - Conditions and Counters\n"
                              "  - condition - Assigns a condition to the given character. Option to add in a numeric value. Option to set it to autodecrement, which will decrease the value by 1 at the end of the character's turn until it reaches 0, where it is automatically deleted. Default is a static value which does not auto-decrement.\n"
                              "  - counter - Assigns a custom counter to the character. Similar to a condition, except it is only showed on the tracker during the character's turn. Custom counters for NPCs do not display on the non-gm tracker."
                              "```", ephemeral=True)
        elif command == 'cc_edit':
            await ctx.respond("```"
                              "cc_edit - Edit or Delete Counters or Conditions\n"
                              "  - edit - Inputs the character's name, the name of the condition and the value, which will overwrite the previous counter/condition\n"
                              "  - delete - Deletes the indicated condition or counter"
                              "```", ephemeral=True)
        elif command == 'cc_show':
            await ctx.respond("```"
                              "cc_show - Show Custom Counters\n"
                              "  - Displays a popup visible only to the user which displays the custom counters for the selected character. Only the GM can see the custom counters of NPCs.\n"
                              "```", ephemeral=True)
        else:
            await ctx.respond('Invalid choice', ephemeral=True)




def setup(bot):
    bot.add_cog(HelpCog(bot))
