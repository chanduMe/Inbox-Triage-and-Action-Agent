import os
import sys
import datetime
from dotenv import load_dotenv

# Ensure we load environment variables
load_dotenv(override=True)

from mcp_client import WorkspaceMCPClient
from agent import TriageAgent

class MockWorkspaceMCPClient(WorkspaceMCPClient):
    """
    Mock Workspace MCP Client that simulates calls to Gmail and Calendar APIs
    without requiring credentials or network access.
    """
    def __init__(self):
        self.credentials = None

    def search_threads(self, query: str) -> dict:
        return {"threads": [{"id": "thread_01"}, {"id": "thread_02"}, {"id": "thread_03"}]}

    def get_thread(self, thread_id: str) -> dict:
        # Mock emails corresponding to the simulation scenario
        # Jane requests a meeting "tomorrow at 3 PM" for 30 minutes
        # Boss has an urgent feedback request
        # Python Weekly is a newsletter/FYI
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        
        threads_db = {
            "thread_01": {
                "id": "thread_01",
                "messages": [{
                    "id": "msg_01",
                    "from": "news@pythonweekly.com",
                    "to": "user@example.com",
                    "date": "2026-06-25T10:00:00",
                    "subject": "Python Weekly - Issue 654",
                    "plaintextBody": "Hi readers,\nHere are the top stories this week:\n1. PEP 744: Python Packaging\n2. Asyncio performance tips...\nBest,\nPython Weekly"
                }]
            },
            "thread_02": {
                "id": "thread_02",
                "messages": [{
                    "id": "msg_02",
                    "from": "jane.doe@example.com",
                    "to": "user@example.com",
                    "date": datetime.datetime.now().isoformat(),
                    "subject": "Project Sync?",
                    "plaintextBody": f"Hi there,\nCan we meet tomorrow at 3:00 PM for 30 minutes to review the design document?\nThanks,\nJane"
                }]
            },
            "thread_03": {
                "id": "thread_03",
                "messages": [{
                    "id": "msg_03",
                    "from": "boss@example.com",
                    "to": "user@example.com",
                    "date": datetime.datetime.now().isoformat(),
                    "subject": "Urgent: Client Feedback",
                    "plaintextBody": "Hi,\nPlease check the client feedback attached and draft a response today. Very critical.\nBest,\nBoss"
                }]
            }
        }
        return threads_db.get(thread_id, {"id": thread_id, "messages": []})

    def list_events(self, start_time: str, end_time: str, page_size: int = 10) -> dict:
        # Simulate that calendar is free (no conflicts)
        return {"events": []}

    def suggest_time(self, attendee_emails: list, start_time: str, end_time: str, duration_minutes: int = 30) -> dict:
        return {"timeSlots": [{"startTime": start_time, "endTime": end_time}]}

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = None) -> dict:
        print(f"[MOCK Tool Execution] Created Calendar Event: '{summary}' from {start_time} to {end_time}")
        return {"status": "confirmed", "id": "mock_event_123", "summary": summary}

    def create_draft(self, draft: dict) -> dict:
        print(f"[MOCK Tool Execution] Created Email Draft: To: {draft.get('to')}, Subject: {draft.get('subject')}")
        print(f"      Body preview: {draft.get('body')[:60].replace(chr(10), ' ')}...")
        return {"id": "mock_draft_456", "message": {"threadId": draft.get("replyToMessageId"), "labelIds": ["DRAFT"]}}

def main():
    print("==================================================================")
    print("   INBOX TRIAGE & ACTION AGENT - REAL ADK SIMULATED RUN           ")
    print("==================================================================")
    
    # Check Gemini API Key is present
    if not os.environ.get("GEMINI_API_KEY"):
        print("[ERROR] GEMINI_API_KEY environment variable is not set in your .env file.")
        print("Please configure GEMINI_API_KEY in a '.env' file to run the simulation.")
        sys.exit(1)
        
    print("\n[Step 1] Initializing Mock Workspace MCP Client...")
    mock_client = MockWorkspaceMCPClient()
    
    print("\n[Step 2] Retrieving Mock Email Threads...")
    search_res = mock_client.search_threads("is:unread")
    thread_ids = [t["id"] for t in search_res.get("threads", [])]
    print(f" -> Found {len(thread_ids)} mock unread threads: {thread_ids}")
    
    detailed_threads = []
    for tid in thread_ids:
        detailed_threads.append(mock_client.get_thread(tid))
        
    print("\n[Step 3] Running Triage Agent ADK Loop (using local MCP server subprocess)...")
    agent = TriageAgent(mock_client)
    
    try:
        summary_report = agent.run_triage(detailed_threads)
        print("\n=== Inbox Triage & Action Report ===")
        print(summary_report.strip())
        print("====================================")
    except Exception as e:
        print(f"\n[ERROR] Simulation run failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
