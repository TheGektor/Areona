# --- Bot Settings Management ---
import sqlite3
import os

DB_PATH = os.getenv('DATABASE_PATH', 'data/bot.db')

def save_bot_settings(**kwargs):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    for key, value in kwargs.items():
        c.execute('REPLACE INTO bot_settings (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def get_bot_settings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute('SELECT key, value FROM bot_settings')
    settings = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return settings
"""Database models for the ticket system."""

import sqlite3
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path


class DatabaseManager:
    """Manages SQLite database connections and operations."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure the database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize database tables."""
        await self._execute_script("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                ticket_type TEXT DEFAULT 'simple',
                welcome_message TEXT DEFAULT 'Welcome to your ticket!',
                target_channel_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS form_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                question_order INTEGER,
                question_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_settings (guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS ticket_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                role_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_settings (guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                channel_id INTEGER,
                ticket_type TEXT,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'normal',
                claimed_by INTEGER,
                category TEXT,
                custom_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_settings (guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS form_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                question_order INTEGER,
                question_text TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id)
            );
            
            CREATE TABLE IF NOT EXISTS co_owners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                assigned_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_settings (guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS ticket_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                user_id INTEGER,
                note_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id)
            );
            
            CREATE TABLE IF NOT EXISTS ticket_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                user_id INTEGER,
                added_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id)
            );
            
            CREATE TABLE IF NOT EXISTS ticket_transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                created_by INTEGER,
                transcript_url TEXT,
                message_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id)
            );
            
            CREATE TABLE IF NOT EXISTS ticket_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                emoji TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_settings (guild_id)
            );
        """)
    
    async def _execute_script(self, script: str):
        """Execute a SQL script asynchronously."""
        def _execute():
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(script)
                conn.commit()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _execute)
    
    async def execute(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        def _execute():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
    
    async def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a SELECT query and return first result."""
        results = await self.execute(query, params)
        return results[0] if results else None
    
    async def execute_write(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows or last row id."""
        def _execute():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
