# VirtualGM

A discord bot focused on enhancing the play by Post ttRPG experience.

Goals:
- Provide a light weight streamlined experience
- Develop an easy to use, system agnostic initiative tracker
- The initiative tracker should be able to go from importing the bot, to basic combat within three minutes.
- Additional functionality which adds to the user experience but is not essential to the basic running of the tracker


This project uses the py-cord library for interfacing with discord. 

# How To Use VirtualGM:

## Initial Setup
- To set up the bot, simply run the **/admin start** command. Three inputs will be required, the player channel, the gm channel and the username of the gm.
  - The GM channel will show a more verbose tracker, and will receive secret rolls.
  - Make sure that VirtualGM has the 'send messages' permissions in both of the channels.
  - Virtual GM can be set up to have multiple simultaneous tables in your server.  To allow this, each table is tied to a pair of channels, and the tracker functions will not work outside of these channels.  Channels cannot be changed once they are set, and one channel cannot house multiple tables.

## Command Reference

### Dice Roller
- Dice are rolled with the **/r** slash command.
- The format is XdY+Z Label (e.g 1d20+7 Initiative)
- The dice roller will accept complex strings of dice (e.g 2d8+3d6-1d4+2)
- The optional secret command with the dice roller will send the result to the GM channel if the channel used has an initiative tracker set up.

### Admin Commands
- **/admin start** - The command to initialize the tracker in the selected channels 
- **/admin tracker** - Contains useful administrative tools for the initiative tracker
  - _transfer gm_ - Transfers the GM permissions to another user
  - _reset trackers_ - Will post and pin new copies of the trackers. Run this if the old tracker is deleted or lost for some reason.
- **/admin options** - View and toggle additional modules
  - _View Modules_ - Displays the current availible modules and if they are enabled for this table
  - _Timekeeper_ - Toggles the Timekeeper Module (See below for details)
    - Optional second input to set the number of seconds elapse per round. Default is 6 (D&D/Pathfinder)
  - _Block Initiative_ - This will toggle block initiative when the next initiative is started or advanced.

### Initiative Tracker Commands
 - **/i add** - Add a PC or NPC
   - takes the argument player with the choice of player or NPC. NPCs have their health obscured and do not show custom counters on the non-gm tracker.
   - An optional argument of _initiative_ can be given to set or roll initiative during the creation of the character.
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
   - _condition_ - Assigns a condition to the given character. 
     - Option to add in a numeric value. 
     - Option to set it to auto-decrement, which will decrease the value by 1 at the end of the character's turn until it reaches 0, where it is automatically deleted. Default is a static value which does not auto-decrement.
       - NOTE: If Block Initiative is active, conditions will auto-decrement at the beginning of the block instead.
   - _counter_ - Assigns a custom counter to the character. 
     - Similar to a condition, except it is only showed on the tracker during the character's turn. 
     - Custom counters for NPCs do not display on the non-gm tracker.  
 - **/i cc_edit** - Edit or Delete Counters or Conditions
   - _edit_ - Inputs the character's name, the name of the condition and the value, which will overwrite the previous counter/condition
   - _delete_ - Deletes the indicated condition or counter
 - **/i cc_show** - Show Custom Counters
   - Displays a popup visible only to the user which displays the custom counters for the selected character. 
   - Only the GM can see the custom counters of NPCs.
 
### Macro Commands
- **/m** - Roll Macro 
  - Select the character and the macro and VirtualGM will roll it for you. The options secret argument will send the roll to the GM instead.
- **/macro create** - Create a Macro
  - Select a character which you have control over and input the name of the macro and the string to roll (XdY+Z format).
  - Note: The bot will not validate the roll string at the time of creation, so if the syntax of the roll is invalid, the bot will still except the macro, although errors will be given when you attempt to use it.
- **/macro remove** - Remove a Macro
  - Select the character and the macro, and this will delete it

### Timekeeping Commands - Requires timekeeping module to be active
- Note: Time is measured from an arbitrary start of the campaign. (Year 1). Do not try to set it to a particular year (aka 1542) as this may cause issues with proper timekeeping.  VirtualGM uses the standard gregorian calandar, but is sanitized of day and month names, reporting numnbers instead. So months will have 30/31 days (except month 2, which will have 28 or 29 days)
- **/time advance** - advances the time by the selected amount
- **/time set** - Sets the date and time to the selected date / time