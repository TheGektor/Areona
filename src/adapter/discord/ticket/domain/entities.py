"""Domain entities for the ticket system."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from enum import Enum


class TicketType(Enum):
    """Types of tickets."""
    SIMPLE = "simple"
    FORM = "form"


class TicketStatus(Enum):
    """Status of tickets."""
    OPEN = "open"
    CLOSED = "closed"


class TicketPriority(Enum):
    """Priority levels for tickets."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class FormQuestion:
    """Represents a form question."""
    order: int
    text: str
    id: Optional[int] = None


@dataclass
class FormResponse:
    """Represents a form response."""
    question_order: int
    question_text: str
    response_text: str
    id: Optional[int] = None


@dataclass
class GuildSettings:
    """Represents guild ticket settings."""
    guild_id: int
    ticket_type: TicketType = TicketType.SIMPLE
    welcome_message: str = "Welcome to your ticket!"
    target_channel_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Ticket:
    """Represents a ticket."""
    guild_id: int
    user_id: int
    channel_id: int
    ticket_type: TicketType
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.NORMAL
    claimed_by: Optional[int] = None
    category: Optional[str] = None
    custom_name: Optional[str] = None
    last_activity: Optional[datetime] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    form_responses: Optional[List[FormResponse]] = None


@dataclass
class TicketRole:
    """Represents a role with access to tickets."""
    guild_id: int
    role_id: int
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class CoOwner:
    """Represents a co-owner of a guild."""
    guild_id: int
    user_id: int
    assigned_by: int
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class TicketNote:
    """Represents an internal note for a ticket."""
    ticket_id: int
    user_id: int
    note_text: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class TicketParticipant:
    """Represents a participant added to a ticket."""
    ticket_id: int
    user_id: int
    added_by: int
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class TicketTranscript:
    """Represents a ticket transcript."""
    ticket_id: int
    created_by: int
    transcript_url: str
    message_count: int = 0
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class TicketCategory:
    """Represents a ticket category."""
    guild_id: int
    name: str
    description: Optional[str] = None
    emoji: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
