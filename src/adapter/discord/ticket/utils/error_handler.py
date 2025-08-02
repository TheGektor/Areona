"""Error handling utilities for the ticket system."""

import discord
import logging
import traceback
from typing import Optional
from ..utils.helpers import create_error_embed
from ..data.templates import get_error_message


logger = logging.getLogger(__name__)


class TicketError(Exception):
    """Base exception for ticket system errors."""
    
    def __init__(self, message: str, error_type: str = "general"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class ConfigurationError(TicketError):
    """Error related to ticket system configuration."""
    
    def __init__(self, message: str):
        super().__init__(message, "configuration")


class PermissionError(TicketError):
    """Error related to permissions."""
    
    def __init__(self, message: str):
        super().__init__(message, "permission")


class ValidationError(TicketError):
    """Error related to input validation."""
    
    def __init__(self, message: str):
        super().__init__(message, "validation")


async def handle_command_error(
    interaction: discord.Interaction,
    error: Exception,
    ephemeral: bool = True
) -> None:
    """Handle command errors with appropriate user feedback."""
    
    # Log the error
    logger.error(f"Command error in {interaction.command.name if interaction.command else 'unknown'}: {error}")
    logger.error(traceback.format_exc())
    
    # Determine error message
    if isinstance(error, TicketError):
        embed = create_error_embed("Ошибка", error.message)
    elif isinstance(error, discord.Forbidden):
        embed = create_error_embed(
            "Недостаточно прав",
            get_error_message("bot_missing_permissions")
        )
    elif isinstance(error, discord.NotFound):
        embed = create_error_embed(
            "Не найдено",
            "Запрашиваемый ресурс не найден."
        )
    elif isinstance(error, discord.HTTPException):
        embed = create_error_embed(
            "Ошибка Discord API",
            "Произошла ошибка при взаимодействии с Discord. Попробуйте позже."
        )
    else:
        embed = create_error_embed(
            "Неизвестная ошибка",
            "Произошла неожиданная ошибка. Обратитесь к администратору."
        )
    
    # Send error message
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
    except discord.HTTPException:
        # If we can't send the error message, log it
        logger.error(f"Failed to send error message for command {interaction.command.name if interaction.command else 'unknown'}")


def validate_guild_context(interaction: discord.Interaction) -> None:
    """Validate that command is used in a guild context."""
    if not interaction.guild:
        raise ValidationError("Эта команда может использоваться только на сервере.")


def validate_bot_permissions(
    channel: discord.TextChannel,
    bot_member: discord.Member,
    required_permissions: list
) -> None:
    """Validate that bot has required permissions in channel."""
    permissions = channel.permissions_for(bot_member)
    
    missing_permissions = []
    for perm_name in required_permissions:
        if not getattr(permissions, perm_name, False):
            missing_permissions.append(perm_name)
    
    if missing_permissions:
        raise PermissionError(
            f"У бота отсутствуют необходимые права: {', '.join(missing_permissions)}"
        )


async def safe_delete_channel(
    channel: discord.TextChannel,
    reason: str = "Ticket closed",
    delay: int = 0
) -> bool:
    """Safely delete a channel with error handling."""
    try:
        if delay > 0:
            import asyncio
            await asyncio.sleep(delay)
        
        await channel.delete(reason=reason)
        return True
    except discord.Forbidden:
        logger.error(f"No permission to delete channel {channel.id}")
        return False
    except discord.NotFound:
        logger.warning(f"Channel {channel.id} already deleted")
        return True
    except discord.HTTPException as e:
        logger.error(f"Failed to delete channel {channel.id}: {e}")
        return False


async def safe_send_message(
    channel: discord.abc.Messageable,
    content: str = None,
    embed: discord.Embed = None,
    view: discord.ui.View = None
) -> Optional[discord.Message]:
    """Safely send a message with error handling."""
    try:
        return await channel.send(content=content, embed=embed, view=view)
    except discord.Forbidden:
        logger.error(f"No permission to send message in channel {getattr(channel, 'id', 'DM')}")
        return None
    except discord.HTTPException as e:
        logger.error(f"Failed to send message: {e}")
        return None


async def safe_edit_message(
    message: discord.Message,
    content: str = None,
    embed: discord.Embed = None,
    view: discord.ui.View = None
) -> bool:
    """Safely edit a message with error handling."""
    try:
        await message.edit(content=content, embed=embed, view=view)
        return True
    except discord.Forbidden:
        logger.error(f"No permission to edit message {message.id}")
        return False
    except discord.NotFound:
        logger.warning(f"Message {message.id} not found")
        return False
    except discord.HTTPException as e:
        logger.error(f"Failed to edit message {message.id}: {e}")
        return False


def log_user_action(
    user: discord.Member,
    action: str,
    details: str = "",
    guild: discord.Guild = None
) -> None:
    """Log user actions for audit purposes."""
    guild_info = f" in {guild.name} ({guild.id})" if guild else ""
    logger.info(f"User {user} ({user.id}) performed action: {action}{guild_info}. Details: {details}")


class ErrorHandler:
    """Centralized error handler for the ticket system."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def handle_interaction_error(
        self,
        interaction: discord.Interaction,
        error: Exception
    ) -> None:
        """Handle errors from slash command interactions."""
        await handle_command_error(interaction, error)
    
    async def handle_view_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        view: discord.ui.View
    ) -> None:
        """Handle errors from UI view interactions."""
        self.logger.error(f"View error in {view.__class__.__name__}: {error}")
        await handle_command_error(interaction, error)
    
    def log_error(
        self,
        error: Exception,
        context: str = "",
        user: discord.Member = None,
        guild: discord.Guild = None
    ) -> None:
        """Log an error with context information."""
        context_info = f" Context: {context}" if context else ""
        user_info = f" User: {user} ({user.id})" if user else ""
        guild_info = f" Guild: {guild.name} ({guild.id})" if guild else ""
        
        self.logger.error(f"Error{context_info}{user_info}{guild_info}: {error}")
        self.logger.error(traceback.format_exc())


# Global error handler instance
error_handler = ErrorHandler()
