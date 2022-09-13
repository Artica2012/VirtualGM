import datetime

import discord


class QuerySelectButton(discord.ui.Button):
    def __init__(self, name:str, id:str, link:str):
        self.link = link
        super().__init__(
            label=name,
            style=discord.ButtonStyle.primary,
            custom_id=id,
        )

    async def callback(self, interaction: discord.Interaction):
        #Called when button is pressed
        user = interaction.user
        message = interaction.message
        await message.delete()
        embed = discord.Embed(
            title= self.label,
            timestamp=datetime.datetime.now(),
            description=self.link
        )
        await interaction.response.send_message(
            embed=embed
        )


class QueryLinkButton(discord.ui.Button):
    def __init__(self,name: str,  link: str):
        """A button for one role."""
        super().__init__(
            label=name,
            style=discord.ButtonStyle.link,
            url= link
        )

# Button to delete a condition in the init condition table
class ConditionDeleteButton(discord.ui.Button):
    def __init__(self, id:int):
        self.id = id
        super().__init__(
            label='Delete',
            style=discord.ButtonStyle.primary,
            custom_id=str(id)
        )

    async def callback(self, interaction: discord.Interaction):
        # Called when button is pressed
        message = interaction.message
        await message.delete()
