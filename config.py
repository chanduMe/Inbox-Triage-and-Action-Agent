import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

# Google Workspace MCP Server Endpoints
GMAIL_MCP_URL = "https://gmailmcp.googleapis.com/mcp/v1"
CALENDAR_MCP_URL = "https://calendarmcp.googleapis.com/mcp/v1"

# OAuth Scopes required for Gmail & Calendar operations
# We request modify access to read/draft emails and full calendar access to check/create events.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar"
]

# OAuth Local Callback Configuration
REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/"
