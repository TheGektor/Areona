"""Utility functions for the ticket system."""

import discord
from typing import List, Optional
from ..config.settings import Settings
from ..domain.entities import FormResponse


def create_embed(
    title: str,
    description: str = "",
    color: int = Settings.COLOR_INFO,
    fields: Optional[List[tuple]] = None
) -> discord.Embed:
    """Create a Discord embed with consistent styling."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    
    return embed


def create_success_embed(title: str, description: str = "") -> discord.Embed:
    """Create a success embed."""
    return create_embed(title, description, Settings.COLOR_SUCCESS)


def create_error_embed(title: str, description: str = "") -> discord.Embed:
    """Create an error embed."""
    return create_embed(title, description, Settings.COLOR_ERROR)


def create_warning_embed(title: str, description: str = "") -> discord.Embed:
    """Create a warning embed."""
    return create_embed(title, description, Settings.COLOR_WARNING)


def create_form_responses_embed(
    user: discord.Member,
    responses: List[FormResponse]
) -> discord.Embed:
    """Create an embed displaying form responses."""
    embed = discord.Embed(
        title="📝 New Ticket Form Submission",
        description=f"**User:** {user.mention}\n**User ID:** {user.id}",
        color=Settings.COLOR_INFO
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    
    for response in responses:
        embed.add_field(
            name=f"❓ {response.question_text}",
            value=response.response_text[:1024],  # Discord field value limit
            inline=False
        )
    
    embed.timestamp = discord.utils.utcnow()
    return embed


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


async def send_dm_safely(user: discord.Member, embed: discord.Embed) -> bool:
    """Send a DM to user safely, return True if successful."""
    try:
        await user.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


def format_role_list(roles: List[discord.Role]) -> str:
    """Format a list of roles for display."""
    if not roles:
        return "None"
    return ", ".join([role.mention for role in roles])


def validate_channel_permissions(
    channel: discord.TextChannel,
    bot_member: discord.Member
) -> bool:
    """Check if bot has necessary permissions in channel."""
    permissions = channel.permissions_for(bot_member)
    required_perms = [
        permissions.read_messages,
        permissions.send_messages,
        permissions.embed_links,
        permissions.manage_channels
    ]
    return all(required_perms)
