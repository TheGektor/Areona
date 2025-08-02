import os
try:
    from dotenv import load_dotenv
except ImportError:
    raise ImportError("Missing 'python-dotenv'. Install with 'pip install python-dotenv'.")
try:
    from src.adapter.discord.bot import DiscordBot
except ImportError as e:
    raise ImportError(f"Could not import DiscordBot: {e}\nCheck your project structure and dependencies.")


def main():
    """Main entry point for the Discord bot."""
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("DISCORD_TOKEN not found in environment variables. Please set it in your .env file.")
    try:
        bot = DiscordBot()
        bot.run(token)
    except Exception as e:
        print(f"Error starting Discord bot: {e}")
        raise


if __name__ == "__main__":
    main()