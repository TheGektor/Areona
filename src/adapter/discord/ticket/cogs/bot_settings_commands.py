import discord
from discord import app_commands, Interaction
from discord.ext import commands
from src.adapter.discord.ticket.database.models import save_bot_settings, get_bot_settings

class BotSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bot-settings", description="Configure bot settings in a specific channel.")
    @app_commands.describe(channel="Channel for bot settings")
    async def settings_command(self, interaction: Interaction, channel: discord.TextChannel):
        # Save the settings channel in the database
        save_bot_settings(channel_id=channel.id)
        settings = get_bot_settings()
        embed = discord.Embed(title="Bot Settings", description="Configure the bot using the buttons below.")
        # Add current settings to embed
        for key, value in settings.items():
            embed.add_field(name=key, value=str(value), inline=False)
        # Send embed with buttons and text input
        view = BotSettingsView()
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Settings channel set to {channel.mention}", ephemeral=True)

class BotSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeDropdown())

    @discord.ui.button(label="Edit Welcome Message", style=discord.ButtonStyle.primary, custom_id="edit_welcome")
    async def edit_welcome(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WelcomeMessageModal())

class TicketTypeDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Simple", value="simple", description="Simple ticket: private channel with welcome message"),
            discord.SelectOption(label="Form", value="form", description="Form ticket: collect answers and send to channel")
        ]
        super().__init__(placeholder="Choose ticket type...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        save_bot_settings(ticket_type=self.values[0])
        await interaction.response.send_message(f"Ticket type set to: {self.values[0]}", ephemeral=True)

class WelcomeMessageModal(discord.ui.Modal, title="Edit Welcome Message"):
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.long,
        placeholder="Example: Добро пожаловать в ваш тикет! Пожалуйста, опишите вашу проблему."
    )

    async def on_submit(self, interaction: Interaction):
        # Save new welcome message to database
        save_bot_settings(welcome_message=self.welcome_message.value)
        await interaction.response.send_message("Welcome message updated!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BotSettings(bot))
