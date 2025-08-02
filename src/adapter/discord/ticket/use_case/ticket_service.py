"""Use cases for ticket system operations."""

import discord
from typing import List, Optional, Tuple
from ..repository.ticket_repository import TicketRepository
from ..domain.entities import (
    GuildSettings, Ticket, TicketRole, FormQuestion, 
    FormResponse, TicketType, TicketStatus
)
from ..config.settings import Settings


class TicketService:
    """Service for ticket system business logic."""
    
    def __init__(self, repository: TicketRepository):
        self.repository = repository
    
    async def setup_guild_settings(
        self, 
        guild_id: int, 
        ticket_type: TicketType,
        welcome_message: str,
        target_channel_id: Optional[int] = None
    ) -> GuildSettings:
        """Setup or update guild ticket settings."""
        settings = GuildSettings(
            guild_id=guild_id,
            ticket_type=ticket_type,
            welcome_message=welcome_message,
            target_channel_id=target_channel_id
        )
        await self.repository.save_guild_settings(settings)
        return settings
    
    async def get_guild_settings(self, guild_id: int) -> Optional[GuildSettings]:
        """Get guild settings."""
        return await self.repository.get_guild_settings(guild_id)
    
    async def setup_form_questions(self, guild_id: int, questions: List[str]) -> List[FormQuestion]:
        """Setup form questions for a guild."""
        if len(questions) > Settings.MAX_QUESTIONS_PER_FORM:
            raise ValueError(f"Maximum {Settings.MAX_QUESTIONS_PER_FORM} questions allowed")
        
        form_questions = [
            FormQuestion(order=i + 1, text=question)
            for i, question in enumerate(questions)
        ]
        
        await self.repository.save_form_questions(guild_id, form_questions)
        return form_questions
    
    async def get_form_questions(self, guild_id: int) -> List[FormQuestion]:
        """Get form questions for a guild."""
        return await self.repository.get_form_questions(guild_id)
    
    async def add_ticket_role(self, guild_id: int, role_id: int) -> None:
        """Add a role that can access tickets."""
        await self.repository.add_ticket_role(guild_id, role_id)
    
    async def remove_ticket_role(self, guild_id: int, role_id: int) -> bool:
        """Remove a ticket role."""
        return await self.repository.remove_ticket_role(guild_id, role_id)
    
    async def get_ticket_roles(self, guild_id: int) -> List[TicketRole]:
        """Get ticket roles for a guild."""
        return await self.repository.get_ticket_roles(guild_id)
    
    async def create_simple_ticket(
        self, 
        guild: discord.Guild, 
        user: discord.Member,
        settings: GuildSettings
    ) -> Tuple[discord.TextChannel, Ticket]:
        """Create a simple ticket channel."""
        # Create private channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add ticket roles
        ticket_roles = await self.get_ticket_roles(guild.id)
        for ticket_role in ticket_roles:
            role = guild.get_role(ticket_role.role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        channel_name = f"{Settings.TICKET_CHANNEL_PREFIX}{user.display_name}".lower()
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=None,  # You can add category logic here
            reason=f"Ticket created by {user}"
        )
        
        # Create ticket record
        ticket = Ticket(
            guild_id=guild.id,
            user_id=user.id,
            channel_id=channel.id,
            ticket_type=TicketType.SIMPLE
        )
        
        ticket_id = await self.repository.create_ticket(ticket)
        ticket.id = ticket_id
        
        return channel, ticket
    
    async def create_form_ticket(
        self,
        guild: discord.Guild,
        user: discord.Member,
        settings: GuildSettings,
        responses: List[FormResponse]
    ) -> Ticket:
        """Create a form ticket and post to target channel."""
        # Create ticket record
        ticket = Ticket(
            guild_id=guild.id,
            user_id=user.id,
            channel_id=settings.target_channel_id or 0,  # Will be updated if channel created
            ticket_type=TicketType.FORM
        )
        
        ticket_id = await self.repository.create_ticket(ticket)
        ticket.id = ticket_id
        
        # Save form responses
        await self.repository.save_form_responses(ticket_id, responses)
        
        return ticket
    
    async def close_ticket(self, channel_id: int) -> Optional[Ticket]:
        """Close a ticket."""
        ticket = await self.repository.get_ticket_by_channel(channel_id)
        if ticket and ticket.status == TicketStatus.OPEN:
            await self.repository.close_ticket(ticket.id)
            ticket.status = TicketStatus.CLOSED
            return ticket
        return None
    
    async def get_ticket_by_channel(self, channel_id: int) -> Optional[Ticket]:
        """Get ticket by channel ID."""
        return await self.repository.get_ticket_by_channel(channel_id)
    
    async def add_co_owner(self, guild_id: int, user_id: int, assigned_by: int) -> None:
        """Add a co-owner."""
        await self.repository.add_co_owner(guild_id, user_id, assigned_by)
    
    async def remove_co_owner(self, guild_id: int, user_id: int) -> bool:
        """Remove a co-owner."""
        return await self.repository.remove_co_owner(guild_id, user_id)
    
    async def is_authorized(self, guild: discord.Guild, user: discord.Member) -> bool:
        """Check if user is authorized to manage tickets (owner or co-owner)."""
        if guild.owner_id == user.id:
            return True
        
        return await self.repository.is_co_owner(guild.id, user.id)
