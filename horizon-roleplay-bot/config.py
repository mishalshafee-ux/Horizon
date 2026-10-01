import os

from dotenv import load_dotenv

load_dotenv()


def get_id(name: str) -> int:
    """Read a Discord ID from the environment, returning 0 if unset/invalid."""
    value = os.getenv(name, "").strip()
    return int(value) if value.isdigit() else 0


# Bot and server
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = get_id("GUILD_ID")

# Welcome and information channels
WELCOME_CHANNEL_ID = get_id("WELCOME_CHANNEL_ID")
INFORMATION_CHANNEL_ID = get_id("INFORMATION_CHANNEL_ID")

# Ticket routing: each ticket type has its own category and staff role
GENERAL_TICKET_CATEGORY_ID = get_id("GENERAL_TICKET_CATEGORY_ID")
GENERAL_TICKET_ROLE_ID = get_id("GENERAL_TICKET_ROLE_ID")

MANAGEMENT_TICKET_CATEGORY_ID = get_id("MANAGEMENT_TICKET_CATEGORY_ID")
MANAGEMENT_TICKET_ROLE_ID = get_id("MANAGEMENT_TICKET_ROLE_ID")

IA_TICKET_CATEGORY_ID = get_id("IA_TICKET_CATEGORY_ID")
IA_TICKET_ROLE_ID = get_id("IA_TICKET_ROLE_ID")

# Sessions
SESSION_CHANNEL_ID = get_id("SESSION_CHANNEL_ID")
SESSION_HOST_ROLE_ID = get_id("SESSION_HOST_ROLE_ID")

# Verification
VERIFY_ROLE_ID = get_id("VERIFY_ROLE_ID")

# Daily Bible verse channel
BIBLE_CHANNEL_ID = get_id("BIBLE_CHANNEL_ID")

# ER:LC API
ERLC_API_KEY = os.getenv("ERLC_API_KEY", "").strip()
