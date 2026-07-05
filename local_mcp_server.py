import sys
import re
from fastmcp import FastMCP

mcp = FastMCP("Concierge Local Agent Server")

@mcp.tool
def analyze_urgency(body: str) -> str:
    """
    Analyze the urgency of the email body.
    Returns: 'High', 'Medium', or 'Low' urgency.
    """
    body_lower = body.lower()
    if any(word in body_lower for word in ["urgent", "asap", "critical", "immediately", "today"]):
        return "High"
    if any(word in body_lower for word in ["tomorrow", "soon", "next week"]):
        return "Medium"
    return "Low"

@mcp.tool
def sanitize_email_addresses(text: str) -> str:
    """
    Sanitizes email addresses from text by replacing them with [REDACTED_EMAIL]
    to protect user privacy.
    """
    return re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', text)

if __name__ == "__main__":
    mcp.run()
