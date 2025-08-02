"""Test script for basic bot functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.adapter.discord.ticket.database.models import DatabaseManager
from src.adapter.discord.ticket.repository.ticket_repository import TicketRepository
from src.adapter.discord.ticket.use_case.ticket_service import TicketService
from src.adapter.discord.ticket.domain.entities import TicketType, GuildSettings, FormQuestion
from src.adapter.discord.ticket.config.settings import Settings


async def test_database_initialization():
    """Test database initialization."""
    print("🔧 Testing database initialization...")
    
    # Use test database
    test_db_path = "test_bot.db"
    db_manager = DatabaseManager(test_db_path)
    
    try:
        await db_manager.initialize()
        print("✅ Database initialized successfully")
        
        # Test basic query
        result = await db_manager.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in result]
        expected_tables = ['guild_settings', 'form_questions', 'ticket_roles', 'tickets', 'form_responses', 'co_owners']
        
        for table in expected_tables:
            if table in tables:
                print(f"✅ Table '{table}' created")
            else:
                print(f"❌ Table '{table}' missing")
        
        return db_manager
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return None


async def test_repository_operations(db_manager):
    """Test repository operations."""
    print("\n📊 Testing repository operations...")
    
    repository = TicketRepository(db_manager)
    test_guild_id = 123456789
    
    try:
        # Test guild settings
        settings = GuildSettings(
            guild_id=test_guild_id,
            ticket_type=TicketType.SIMPLE,
            welcome_message="Test welcome message",
            target_channel_id=987654321
        )
        
        await repository.save_guild_settings(settings)
        print("✅ Guild settings saved")
        
        retrieved_settings = await repository.get_guild_settings(test_guild_id)
        if retrieved_settings and retrieved_settings.guild_id == test_guild_id:
            print("✅ Guild settings retrieved")
        else:
            print("❌ Guild settings retrieval failed")
        
        # Test form questions
        questions = [
            FormQuestion(order=1, text="Test question 1"),
            FormQuestion(order=2, text="Test question 2")
        ]
        
        await repository.save_form_questions(test_guild_id, questions)
        print("✅ Form questions saved")
        
        retrieved_questions = await repository.get_form_questions(test_guild_id)
        if len(retrieved_questions) == 2:
            print("✅ Form questions retrieved")
        else:
            print(f"❌ Form questions retrieval failed (got {len(retrieved_questions)}, expected 2)")
        
        # Test ticket roles
        test_role_id = 555666777
        await repository.add_ticket_role(test_guild_id, test_role_id)
        print("✅ Ticket role added")
        
        roles = await repository.get_ticket_roles(test_guild_id)
        if any(role.role_id == test_role_id for role in roles):
            print("✅ Ticket role retrieved")
        else:
            print("❌ Ticket role retrieval failed")
        
        # Test co-owners
        test_user_id = 111222333
        test_assigned_by = 444555666
        await repository.add_co_owner(test_guild_id, test_user_id, test_assigned_by)
        print("✅ Co-owner added")
        
        is_co_owner = await repository.is_co_owner(test_guild_id, test_user_id)
        if is_co_owner:
            print("✅ Co-owner check passed")
        else:
            print("❌ Co-owner check failed")
        
        return True
        
    except Exception as e:
        print(f"❌ Repository operations failed: {e}")
        return False


async def test_service_layer(db_manager):
    """Test service layer operations."""
    print("\n🔧 Testing service layer...")
    
    repository = TicketRepository(db_manager)
    service = TicketService(repository)
    test_guild_id = 987654321
    
    try:
        # Test guild settings setup
        settings = await service.setup_guild_settings(
            guild_id=test_guild_id,
            ticket_type=TicketType.FORM,
            welcome_message="Service test welcome message",
            target_channel_id=123123123
        )
        
        if settings.ticket_type == TicketType.FORM:
            print("✅ Service guild settings setup")
        else:
            print("❌ Service guild settings setup failed")
        
        # Test form questions setup
        test_questions = [
            "What is your name?",
            "Describe your issue",
            "When did this happen?"
        ]
        
        form_questions = await service.setup_form_questions(test_guild_id, test_questions)
        if len(form_questions) == 3:
            print("✅ Service form questions setup")
        else:
            print(f"❌ Service form questions setup failed (got {len(form_questions)}, expected 3)")
        
        # Test validation
        try:
            # This should fail due to too many questions
            long_questions = ["Question " + str(i) for i in range(15)]
            await service.setup_form_questions(test_guild_id, long_questions)
            print("❌ Validation failed - should have rejected too many questions")
        except ValueError:
            print("✅ Validation working - rejected too many questions")
        
        return True
        
    except Exception as e:
        print(f"❌ Service layer test failed: {e}")
        return False


async def test_configuration():
    """Test configuration settings."""
    print("\n⚙️ Testing configuration...")
    
    try:
        # Test settings access
        db_path = Settings.get_database_path()
        print(f"✅ Database path: {db_path}")
        
        # Test constants
        if Settings.MAX_QUESTIONS_PER_FORM == 10:
            print("✅ MAX_QUESTIONS_PER_FORM constant")
        else:
            print("❌ MAX_QUESTIONS_PER_FORM constant incorrect")
        
        if Settings.TICKET_CHANNEL_PREFIX == "ticket-":
            print("✅ TICKET_CHANNEL_PREFIX constant")
        else:
            print("❌ TICKET_CHANNEL_PREFIX constant incorrect")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def cleanup_test_files():
    """Clean up test files."""
    print("\n🧹 Cleaning up test files...")
    
    test_files = ["test_bot.db", "test_bot.db-journal"]
    
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"✅ Removed {file}")
            except Exception as e:
                print(f"❌ Failed to remove {file}: {e}")


async def main():
    """Run all tests."""
    print("🚀 Starting Discord Ticket Bot Tests\n")
    
    # Test configuration
    config_ok = await test_configuration()
    
    # Test database
    db_manager = await test_database_initialization()
    if not db_manager:
        print("\n❌ Database tests failed, stopping")
        return
    
    # Test repository
    repo_ok = await test_repository_operations(db_manager)
    
    # Test service layer
    service_ok = await test_service_layer(db_manager)
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Database: {'✅ PASS' if db_manager else '❌ FAIL'}")
    print(f"Repository: {'✅ PASS' if repo_ok else '❌ FAIL'}")
    print(f"Service Layer: {'✅ PASS' if service_ok else '❌ FAIL'}")
    
    all_passed = config_ok and db_manager and repo_ok and service_ok
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 The ticket system is ready to use!")
        print("Next steps:")
        print("1. Create a Discord application and bot")
        print("2. Copy the bot token to .env file")
        print("3. Invite the bot to your server with proper permissions")
        print("4. Run 'python main.py' to start the bot")
    else:
        print("\n⚠️ Please fix the failing tests before using the bot")
    
    # Cleanup
    await cleanup_test_files()


if __name__ == "__main__":
    asyncio.run(main())
