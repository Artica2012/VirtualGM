# VirtualGM

A discord bot focused on enhancing the play by Post ttRPG experience.

Goals:
- Provide a light weight streamlined experience
- Develop an easy to use, system agnostic initiative tracker

It does have some reference/lookup that is D&D 4th edition specific, considering adding lookups to other systems in the future.

This project uses the py-cord library for interfacing with discord. 

## How To Use VirtualGM:

### Initial Setup
- To set up the bot, simply run the /i admin command and choose 'setup'.  
- Once this is done, you should select a channel to be your main dice rolling channel and run the /i admin command and choose 'tracker'.  This will pin  a tracker into the channel for your player's usage.
- Next select a channel for the GM screen. This channel should ideally be hidden from the players but VirtualGM will need message permissions for the channel. Run the /i admin command and select 'gm tracker'.  This channel will show a more verbose tracker, and will receive secret rolls.

### Dice Roller
- Dice are rolled with the /r slash command.
- The format is XdY+Z Label (e.g 1d20+7 Initiative)
- The dice roller will accept complex strings of dice (e.g 2d8+3d6-1d4+2)
- The optional secret command with the dice roller will send the result to the GM channel if it has been set up.

### Initiative Tracker - Commands
 - **/i admin** - Administrative Commands (GM Restricted)
   - _setup_ - Initializes the bot
   - _transfer gm_ - Transfers the GM permissions to another user
   - _tracker_ - posts a pinned tracker into the given channel and assigns it as the active channel. This will deactivate the previous pinned tracker, (although it will not delete nor unpin it, the old pin will just cease to update automatically)
   - _gm tracker_ - posts a pinned gm tracker, which is more verbose and displays NPC hp and counters. It will also assign the channel to act as the GM channel, which will receive secret rolls.
 - **/i add** - Add a PC or NPC
   - takes the argument player with the choice of player or NPC. NPCs have their health obscured and do not show custom counters on the non-gm tracker.
 - **/i manage** - Mange Initiative (GM Restricted)
   - _start_ - Starts Initiative
   - _stop_ - Stops Initiative
   - _delete character_ - takes the argument character and will delete the character out of the tracker. Will not function if it is currently the character's turn.
 - **/i next** - Advance Initiative
 - **/i init** - Assign an initiative value to the character
   - Takes the arguments _character_ which is the character's name and _initiative_ which can be given as a whole numner (e.g. 15) or a dice expression in the form of XdY+Z (e.g 1d20+7)
 - **/i hp** - Adjust HP
   - _Damage_ - Damages the indicated character for inputted amount
   - _Heal_ - Heals the character for the inputted amount
   - _Temporary HP_ - Grants the character the inputted amount of temporary HP. This HP will be subtracted from first and not added to with any healing.
 - **/i cc** - Conditions and Counters
   - _condition_ - Assigns a condition to the given character. Option to add in a numeric value. Option to set it to autodecrement, which will decrease the value by 1 at the end of the character's turn until it reaches 0, where it is automatically deleted. Default is a static value which does not auto-decrement.
   - _counter_ - Assigns a custom counter to the character. Similar to a condition, except it is only showed on the tracker during the character's turn. Custom counters for NPCs do not display on the non-gm tracker.  
 - **/i cc_edit** - Edit or Delete Counters or Conditions
   - _edit_ - Inputs the character's name, the name of the condition and the value, which will overwrite the previous counter/condition
   - _delete_ - Deletes the indicated condition or counter
 - **/i cc_show** - Show Custom Counters
   - Displays a popup visible only to the user which displays the custom counters for the selected character. Only the GM can see the custom counters of NPCs.
 