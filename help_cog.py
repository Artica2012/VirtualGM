# help_cog.py

import os

# imports
import discord
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands
from dotenv import load_dotenv

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
                          "- To set up the bot, simply run the **/admin start** command. Three inputs will be "
                          "required, the player channel, the gm channel and the username of the gm.\n "
                          "- The GM channel will show a more verbose tracker, and will receive secret rolls.\n"
                          "- Make sure that VirtualGM has the 'send messages' permissions in both of the channels.\n"
                          "- Virtual GM can be set up to have multiple simultaneous tables in your server.  To allow "
                          "this, each table is tied to a pair of channels, and the tracker functions will not work "
                          "outside of these channels.  Channels cannot be changed once they are set, and one channel "
                          "cannot house multiple tables.\n```",
                          ephemeral=True)

    @help.command(description="Roller",
                  # guild_ids=[GUILD]
                  )
    async def roller(self, ctx: discord.ApplicationContext):
        await ctx.respond("```"
                          "- Dice are rolled with the **/r** slash command.\n"
                          "- The format is XdY+Z Label (e.g 1d20+7 Initiative)\n"
                          "- The dice roller will accept complex strings of dice (e.g 2d8+3d6-1d4+2)\n"
                          "- The optional secret command with the dice roller will send the result to the GM channel "
                          "if the channel used has an initiative tracker set up. \n "
                          "- The optional dc argument will give a positive (thumbsup) or negative (thumbsdown) to "
                          "indicate if the roll meets or exceeds the given difficulty class.\n"
                          "```", ephemeral=True
                          )

    @help.command(description="Admin")
    async def admin(self, ctx: discord.ApplicationContext):
        await ctx.respond("```"
                          "- **/admin start** - The command to initialize the tracker in the selected channels \n"
                          "- **/admin tracker** - Contains useful administrative tools for the initiative tracker\n"
                          "  - _transfer gm_ - Transfers the GM permissions to another user\n"
                          "  - _reset trackers_ - Will post and pin new copies of the trackers. Run this if the old "
                          "tracker is deleted or lost for some reason. \n"
                          "- **/admin options** - View and toggle additional modules\n"
                          "- _View Modules_ - Displays the current availible modules and if they are enabled for this "
                          "table\n "
                          "  - _Timekeeper_ - Toggles the Timekeeper Module (See below for details)\n"
                          "  - Optional second input to set the number of seconds elapse per round. Default is 6 ("
                          "D&D/Pathfinder)\n "
                          "  - _Block Initiative_ - This will toggle block initiative when the next initiative is "
                          "started or advanced.\n "
                          "```", ephemeral=True)

    @help.command(description="Initiative",
                  # guild_ids=[GUILD]
                  )
    @option('command', choices=[
        'char add', 'char edit', 'char copy', 'manage', 'next', 'init', 'hp', 'cc new', 'cc_edit', 'cc_show'
    ])
    async def initiative(self, ctx: discord.ApplicationContext, command: str):
        if command == 'char add':
            await ctx.respond("```"
                              "add - Add a PC or NPC\n"
                              "- takes the argument player with the choice of player or NPC. NPCs have their health "
                              "- obscured and do not show custom counters on the non-gm tracker. "
                              "- An argument of _initiative_ can be given to set an initiative string (XdY+Z) which will be rolled when initiative is started"
                              "```", ephemeral=True)
        elif command == "char edit":
            await ctx.respond("``` Edit a PC or NPC"
                              "- Edit the max hp and/or initiative string of a character you control"
                              "  ```"
                              )
        elif command == 'char copy':
            await ctx.respond("```Copies a character or NPC including any system specific stats. Does not copy and "
                              "conditions or counters. Will roll a new initiative if initiative is active.```")
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
                              "next - Advance Initiative (or start it)"
                              "```", ephemeral=True)
        elif command == 'init':
            await ctx.respond("```"
                              "init - Assign an initiative value to the character\n"
                              "- Takes the arguments _character_ which is the character's name and _initiative_ which "
                              "can be given as a whole numner (e.g. 15) or a dice expression in the form of XdY+Z ("
                              "e.g 1d20+7). This will override any set initiative string for the next initiative. "
                              "- Can also be used to change initiative while initiative is running."
                              "```", ephemeral=True)
        elif command == 'hp':
            await ctx.respond("```"
                              "hp - Adjust HP\n"
                              "  - Damage - Damages the indicated character for inputted amount\n"
                              "  - Heal - Heals the character for the inputted amount\n"
                              "- Temporary HP - Grants the character the inputted amount of temporary HP. This HP "
                              "will be subtracted from first and not added to with any healing. "
                              "```", ephemeral=True)
        elif command == 'cc new':
            await ctx.respond("```"
                              "- **/cc new** - Conditions and Counters"
                              "  - _condition_ - Assigns a condition to the given character.\n"
                              "    - Option to add in a numeric value.\n"
                              "- Option to set it to auto-decrement, which will decrease the value by 1 at the end of "
                              "the character's turn "
                              "until it reaches 0, where it is automatically deleted. Default is a static value which "
                              "does not auto-decrement.\n "
                              "- NOTE: If Block Initiative is active, conditions will auto-decrement at the beginning "
                              "of the block instead.\n "
                              "  - _counter_ - Assigns a custom counter to the character.\n"
                              "- Similar to a condition, except it is only showed on the tracker during the "
                              "character's turn.\n "
                              "    - Custom counters for NPCs do not display on the non-gm tracker.\n"
                              "```", ephemeral=True)
        elif command == '/cc edit':
            await ctx.respond("```"
                              "cc edit - Edit or Delete Counters or Conditions\n"
                              "- edit - Inputs the character's name, the name of the condition and the value, "
                              "which will overwrite the previous counter/condition\n "
                              "  - delete - Deletes the indicated condition or counter"
                              "```", ephemeral=True)
        elif command == '/cc show':
            await ctx.respond("```"
                              "cc show - Show Custom Counters\n"
                              "- Displays a popup visible only to the user which displays the custom counters for the "
                              "selected character. Only the GM can see the custom counters of NPCs.\n "
                              "```", ephemeral=True)
        else:
            await ctx.respond('Invalid choice', ephemeral=True)

    @help.command(description="Macro",
                  # guild_ids=[GUILD]
                  )
    @option('command', choices=[
        'm', 'create', 'remove', 'remove_all', "bulk_create"])
    async def macro(self, ctx: discord.ApplicationContext, command: str):
        if command == 'm':
            await ctx.respond(
                "```Roll Macro\n"
                "- Select the character and the macro and VirtualGM will roll it for you.The options secret argument "
                "will send the roll to the GM instead.\n"
                "- The optional dc argument will give a positive (thumbsup) or negative (thumbsdown)  to indicate if the"
                " roll meets or exceeds the given difficulty class.``` "
                , ephemeral=True
            )
        elif command == 'create':
            await ctx.respond("```Create a Macro"
                              "- Select a character which you have control over and input the name of the macro and "
                              "the string to roll (XdY+Z format).\n "
                              "- Note: The bot will not validate the roll string at the time of creation, so if the "
                              "syntax of the roll is invalid, the bot will still except the macro, although errors "
                              "will be given when you attempt to use it.\n "
                              '```', ephemeral=True
                              )
        elif command == "remove":
            await ctx.respond("```Remove Macro\n"
                              "- Select the character and the macro, and this will delete it"
                              "```", ephemeral=True
                              )
        elif command == 'remove_all':
            await ctx.respond('```Deletes all macros owned by a given character```', ephemeral=True)
        elif command == 'bulk_create':
            await ctx.respond('```Allows adding multiple macros at one time to the same character\n'
                              '  - Format ins Name, Roll; Name, Roll; Name: Roll.\n'
                              '  - Macro Name and roll separated by a comma, and each macro separated by a semicolon.```',
                              ephemeral=True)
        else:
            await ctx.respond('Invalid choice', ephemeral=True)

    @help.command(description="Timekeeping",
                  # guild_ids=[GUILD]
                  )
    @option('command', choices=[
        'advance', 'set'])
    async def timekeeping(self, ctx: discord.ApplicationContext, command: str):
        if command == 'advance':
            await ctx.respond(
                "```advance\n"
                "- advances the time by the selected amount``` "
                , ephemeral=True
            )
        elif command == 'set':
            await ctx.respond("```Set time\n"
                              "- Sets the date and time to the selected date / time\n"
                              "- Note: Time is measured from an arbitrary start of the campaign. (Year 1). Do not try "
                              "to set it to a particular year (aka 1542) as this may cause issues with proper "
                              "timekeeping.  VirtualGM uses the standard gregorian calandar, but is sanitized of day "
                              "and month names, reporting numnbers instead. So months will have 30/31 days (except "
                              "month 2, which will have 28 or 29 days) "
                              '```', ephemeral=True
                              )
        else:
            await ctx.respond('Invalid choice', ephemeral=True)

    @help.command(description="Automation",
                      # guild_ids=[GUILD]
                      )
    @option('command', choices=[
            'attack', 'save'])
    async def a(self, ctx: discord.ApplicationContext, command: str):
        if command == 'attack':
            await ctx.respond(
                "```attack\n"
                "- rolls an automatic attack``` "
                , ephemeral=True
            )
        elif command == 'save':
            await ctx.respond("```Save\n"
                              "- Rolls an automated Saving Throw\n"
                              '```', ephemeral=True
                              )
        else:
            await ctx.respond('Invalid choice', ephemeral=True)



def setup(bot):
    bot.add_cog(HelpCog(bot))
