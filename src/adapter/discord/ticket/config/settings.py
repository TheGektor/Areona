"""Configuration settings for the ticket system."""

import os
from typing import Optional


class Settings:
    """Bot configuration settings."""
    
    # Database settings
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'data/bot.db')
    
    # Ticket settings
    MAX_QUESTIONS_PER_FORM: int = 10
    TICKET_CHANNEL_PREFIX: str = "ticket-"
    
    # Embed colors
    COLOR_SUCCESS: int = 0x00ff00
    COLOR_ERROR: int = 0xff0000
    COLOR_INFO: int = 0x0099ff
    COLOR_WARNING: int = 0xffaa00
    
    # Timeouts
    FORM_TIMEOUT_SECONDS: int = 300  # 5 minutes
    
    @classmethod
    def get_database_path(cls) -> str:
        """Get the database path, creating directory if needed."""
        db_path = cls.DATABASE_PATH
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return db_path
