"""Repository for ticket-related database operations."""

from typing import List, Optional
from ..database.models import DatabaseManager
from ..domain.entities import (
    GuildSettings, Ticket, TicketRole, FormQuestion, 
    FormResponse, CoOwner, TicketType, TicketStatus
)


class TicketRepository:
    """Repository for ticket system data access."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    # Guild Settings
    async def get_guild_settings(self, guild_id: int) -> Optional[GuildSettings]:
        """Get guild settings."""
        result = await self.db.execute_one(
            "SELECT * FROM guild_settings WHERE guild_id = ?",
            (guild_id,)
        )
        if result:
            return GuildSettings(
                guild_id=result['guild_id'],
                ticket_type=TicketType(result['ticket_type']),
                welcome_message=result['welcome_message'],
                target_channel_id=result['target_channel_id']
            )
        return None
    
    async def save_guild_settings(self, settings: GuildSettings) -> None:
        """Save or update guild settings."""
        await self.db.execute_write(
            """INSERT OR REPLACE INTO guild_settings 
               (guild_id, ticket_type, welcome_message, target_channel_id, updated_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (settings.guild_id, settings.ticket_type.value, 
             settings.welcome_message, settings.target_channel_id)
        )
    
    # Form Questions
    async def get_form_questions(self, guild_id: int) -> List[FormQuestion]:
        """Get form questions for a guild."""
        results = await self.db.execute(
            "SELECT * FROM form_questions WHERE guild_id = ? ORDER BY question_order",
            (guild_id,)
        )
        return [
            FormQuestion(
                id=row['id'],
                order=row['question_order'],
                text=row['question_text']
            )
            for row in results
        ]
    
    async def save_form_questions(self, guild_id: int, questions: List[FormQuestion]) -> None:
        """Save form questions for a guild."""
        # Delete existing questions
        await self.db.execute_write(
            "DELETE FROM form_questions WHERE guild_id = ?",
            (guild_id,)
        )
        
        # Insert new questions
        for question in questions:
            await self.db.execute_write(
                "INSERT INTO form_questions (guild_id, question_order, question_text) VALUES (?, ?, ?)",
                (guild_id, question.order, question.text)
            )
    
    # Ticket Roles
    async def get_ticket_roles(self, guild_id: int) -> List[TicketRole]:
        """Get ticket roles for a guild."""
        results = await self.db.execute(
            "SELECT * FROM ticket_roles WHERE guild_id = ?",
            (guild_id,)
        )
        return [
            TicketRole(
                id=row['id'],
                guild_id=row['guild_id'],
                role_id=row['role_id']
            )
            for row in results
        ]
    
    async def add_ticket_role(self, guild_id: int, role_id: int) -> None:
        """Add a ticket role."""
        await self.db.execute_write(
            "INSERT OR IGNORE INTO ticket_roles (guild_id, role_id) VALUES (?, ?)",
            (guild_id, role_id)
        )
    
    async def remove_ticket_role(self, guild_id: int, role_id: int) -> bool:
        """Remove a ticket role. Returns True if removed."""
        affected = await self.db.execute_write(
            "DELETE FROM ticket_roles WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id)
        )
        return affected > 0
    
    # Tickets
    async def create_ticket(self, ticket: Ticket) -> int:
        """Create a new ticket. Returns ticket ID."""
        ticket_id = await self.db.execute_write(
            """INSERT INTO tickets (guild_id, user_id, channel_id, ticket_type, status)
               VALUES (?, ?, ?, ?, ?)""",
            (ticket.guild_id, ticket.user_id, ticket.channel_id, 
             ticket.ticket_type.value, ticket.status.value)
        )
        return ticket_id
    
    async def get_ticket_by_channel(self, channel_id: int) -> Optional[Ticket]:
        """Get ticket by channel ID."""
        result = await self.db.execute_one(
            "SELECT * FROM tickets WHERE channel_id = ?",
            (channel_id,)
        )
        if result:
            return Ticket(
                id=result['id'],
                guild_id=result['guild_id'],
                user_id=result['user_id'],
                channel_id=result['channel_id'],
                ticket_type=TicketType(result['ticket_type']),
                status=TicketStatus(result['status'])
            )
        return None
    
    async def close_ticket(self, ticket_id: int) -> None:
        """Close a ticket."""
        await self.db.execute_write(
            "UPDATE tickets SET status = ?, closed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (TicketStatus.CLOSED.value, ticket_id)
        )
    
    # Form Responses
    async def save_form_responses(self, ticket_id: int, responses: List[FormResponse]) -> None:
        """Save form responses for a ticket."""
        for response in responses:
            await self.db.execute_write(
                """INSERT INTO form_responses 
                   (ticket_id, question_order, question_text, response_text)
                   VALUES (?, ?, ?, ?)""",
                (ticket_id, response.question_order, 
                 response.question_text, response.response_text)
            )
    
    async def get_form_responses(self, ticket_id: int) -> List[FormResponse]:
        """Get form responses for a ticket."""
        results = await self.db.execute(
            "SELECT * FROM form_responses WHERE ticket_id = ? ORDER BY question_order",
            (ticket_id,)
        )
        return [
            FormResponse(
                id=row['id'],
                question_order=row['question_order'],
                question_text=row['question_text'],
                response_text=row['response_text']
            )
            for row in results
        ]
    
    # Co-owners
    async def add_co_owner(self, guild_id: int, user_id: int, assigned_by: int) -> None:
        """Add a co-owner."""
        await self.db.execute_write(
            "INSERT OR IGNORE INTO co_owners (guild_id, user_id, assigned_by) VALUES (?, ?, ?)",
            (guild_id, user_id, assigned_by)
        )
    
    async def remove_co_owner(self, guild_id: int, user_id: int) -> bool:
        """Remove a co-owner. Returns True if removed."""
        affected = await self.db.execute_write(
            "DELETE FROM co_owners WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        return affected > 0
    
    async def get_co_owners(self, guild_id: int) -> List[CoOwner]:
        """Get co-owners for a guild."""
        results = await self.db.execute(
            "SELECT * FROM co_owners WHERE guild_id = ?",
            (guild_id,)
        )
        return [
            CoOwner(
                id=row['id'],
                guild_id=row['guild_id'],
                user_id=row['user_id'],
                assigned_by=row['assigned_by']
            )
            for row in results
        ]
    
    async def is_co_owner(self, guild_id: int, user_id: int) -> bool:
        """Check if user is a co-owner."""
        result = await self.db.execute_one(
            "SELECT 1 FROM co_owners WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        return result is not None
