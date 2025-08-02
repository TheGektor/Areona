"""Main Discord bot class."""

import discord
from discord.ext import commands
from src.adapter.discord.ticket.cogs.bot_settings_commands import setup as setup_bot_settings
import logging
from .ticket.database.models import DatabaseManager
from .ticket.repository.ticket_repository import TicketRepository
from .ticket.use_case.ticket_service import TicketService
from .ticket.config.settings import Settings


class DiscordBot(commands.Bot):
    """Main Discord bot class."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',  # Fallback prefix, we'll use slash commands
            intents=intents,
            help_command=None
        )
        
        # Initialize services
        self.db_manager = DatabaseManager(Settings.get_database_path())
        self.ticket_repository = TicketRepository(self.db_manager)
        self.ticket_service = TicketService(self.ticket_repository)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # Cog registration moved to setup_hook
    
    async def setup_hook(self):
        """Setup hook called when bot is starting."""
        # Initialize database
        await self.db_manager.initialize()
        self.logger.info("Database initialized")
        
        # Load cogs
        await self.load_extension('src.adapter.discord.ticket.cogs.ticket_commands')
        await self.load_extension('src.adapter.discord.ticket.cogs.setup_commands')
        await self.load_extension('src.adapter.discord.ticket.cogs.admin_commands')
        # Register new bot settings cog
        await setup_bot_settings(self)
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            self.logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready."""
        self.logger.info(f'{self.user} has connected to Discord!')
        self.logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for /ticket commands"
            )
        )
    
    async def on_guild_join(self, guild):
        """Called when bot joins a guild."""
        self.logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
    
    async def on_guild_remove(self, guild):
        """Called when bot leaves a guild."""
        self.logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
    
    async def on_command_error(self, ctx, error):
        """Global error handler."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        self.logger.error(f"Command error: {error}")
        
        if ctx.interaction:
            try:
                await ctx.interaction.response.send_message(
                    "An error occurred while processing your command.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                await ctx.interaction.followup.send(
                    "An error occurred while processing your command.",
                    ephemeral=True
                )
