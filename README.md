# VirtualGM

A discord bot focused in enhancing the play by Post ttRPG experience.

Goals:
- Light weight streamlined experience
- System agnostic initiative tracker

It does have some reference/lookup that is D&d 4th edition specific, considering adding lookups to other systems in the future.

This project uses the py-cord library for interfacing with discord. 

## How To Use VirtualGM:

### Initial Setup
- To set up the bot, simply run the /i admin command and choose 'setup'.  
- Once this is done, you should select a channel to be your main dice rolling channel and run the /i admin command and choose 'tracker'.  This will pin  a tracker into the channel for your player's usage.
- Next select a channel for the GM screen. This channel should ideally be hidden from the players but VirtualGM will need permissions for the channel. Run the /i admin command and select 'gm_tracker'.  This channel will show a more verbose tracker, and will receive secret rolls.

### Dice Roller
- Dice are rolled with the /r slash command.
- The format is XdY+Z Label
- The dice roller will accept complex strings of dice (e.g 2d8+3d6-1d4+2)
- The optional secret command with the dice roller will send the result to the GM channel if it has been set up

### Initiative Tracker - Commands
 - /i admin - Administrative Commands
   - setup