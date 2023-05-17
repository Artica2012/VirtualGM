# VirtualGM

A discord bot focused on enhancing the play by Post ttRPG experience.

Goals:
- Provide a light weight streamlined experience
- Develop an easy to use, system agnostic initiative tracker
- The initiative tracker should be able to go from importing the bot, to basic combat within three minutes.
- Additional functionality which adds to the user experience but is not essential to the basic running of the tracker

This project uses the py-cord library for interfacing with discord. 

### Join our discord community:
https://discord.gg/CeF4yeAekQ

# How To Use VirtualGM:

## Initial Setup
- To set up the bot, simply run the **/admin start** command. Three inputs will be required, the player channel, the gm channel and the username of the gm.
  - The GM channel will show a more verbose tracker, and will receive secret rolls.
  - Make sure that VirtualGM has the 'send messages' permissions in both of the channels.
  - Virtual GM can be set up to have multiple simultaneous tables in your server.  To allow this, each table is tied to a pair of channels, and the tracker functions will not work outside of these channels.  Channels cannot be changed once they are set, and one channel cannot house multiple tables.


### Supported Systems
#### System Agnostic Tracker
 - The basic system agnostic tracker. Lacks advanced automation but usable with any system that needs to track initiatve.

#### Pathfinder Second Edition
 - Both a basic Pathfinder 2e and Enhanced Pathfinder 2e module. The Enhanced has increased functionality and automation, but also increased complexity of setup and requires use of google sheets for some home brew.
 - Enhanced Pathfinder 2e is the premier module, and the preferred method of using VirtualGM
 - Documentation
   - Basic Pathfider 2e - https://docs.google.com/document/d/13nJH7xE18fO_SiM-cbCKgq6HbIl3aPIG602rB_nPRik/edit?usp=sharing
   - Enhanced Pathfinder 2e - https://docs.google.com/document/d/1tD9PNXQ-iOBalvzxpTQ9CvuM2jy6Y_S75Rjjof-WRBk/edit?usp=sharing
#### Dungeons and Dragons 4th Edition
   - Dungeons and Dragons 4th Edition

#### Starfinder
 - Documentation
   - https://docs.google.com/document/d/1jCm_b6xE4CsRBOFYaYWU8WB1ake9pjucZMlBspcqhnU/edit?usp=sharing

