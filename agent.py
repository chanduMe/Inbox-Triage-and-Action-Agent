import os
import sys
import datetime
import asyncio
from google.genai import types
from mcp_client import WorkspaceMCPClient
import config

# ADK imports
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

class TriageAgent:
    def __init__(self, mcp_client: WorkspaceMCPClient):
        self.mcp_client = mcp_client

    def run_triage(self, threads: list) -> str:
        """
        Runs the ADK agent loop to triage the email threads using Workspace tools
        and local MCP security/privacy utility tools.
        """
        # Exposed Workspace tools
        
        def list_calendar_events(start_time: str, end_time: str) -> dict:
            """
            Retrieve calendar events for the user's primary calendar between start_time and end_time.
            Use this to check availability or see if there is an existing scheduling conflict.
            Args:
                start_time: Start of range (ISO 8601 string, e.g., '2026-06-25T09:00:00').
                end_time: End of range (ISO 8601 string, e.g., '2026-06-25T17:00:00').
            """
            print(f"[Tool Call] list_calendar_events: {start_time} to {end_time}")
            try:
                return self.mcp_client.list_events(start_time, end_time)
            except Exception as e:
                print(f"[Tool Error] list_calendar_events: {e}")
                return {"error": str(e)}

        def suggest_meeting_time(attendee_emails: list[str], start_time: str, end_time: str, duration_minutes: int = 30) -> dict:
            """
            Suggest available open time slots for a meeting with the specified attendees.
            Args:
                attendee_emails: List of emails of the participants (use ['primary'] to check only the user's primary calendar).
                start_time: Start of search range in ISO 8601 format.
                end_time: End of search range in ISO 8601 format.
                duration_minutes: Length of the desired meeting in minutes.
            """
            print(f"[Tool Call] suggest_meeting_time: {attendee_emails} from {start_time} to {end_time} ({duration_minutes} min)")
            try:
                return self.mcp_client.suggest_time(attendee_emails, start_time, end_time, duration_minutes)
            except Exception as e:
                print(f"[Tool Error] suggest_meeting_time: {e}")
                return {"error": str(e)}

        def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = None) -> dict:
            """
            Create a new calendar event on the user's primary calendar.
            Args:
                summary: Title of the meeting or event.
                start_time: Event start time in ISO 8601 format.
                end_time: Event end time in ISO 8601 format.
                description: Optional description or notes for the event.
            """
            print(f"[Tool Call] create_calendar_event: '{summary}' from {start_time} to {end_time}")
            try:
                return self.mcp_client.create_event(summary, start_time, end_time, description)
            except Exception as e:
                print(f"[Tool Error] create_calendar_event: {e}")
                return {"error": str(e)}

        def create_email_draft(to_emails: list[str], subject: str, body: str, reply_to_message_id: str = None) -> dict:
            """
            Create a draft response email in Gmail.
            Args:
                to_emails: List of recipient email addresses (plain addresses only, e.g. ['recipient@example.com']).
                subject: Subject line of the email draft.
                body: Plain text body of the email.
                reply_to_message_id: Optional ID of the message you are replying to, if this is a threaded reply.
            """
            print(f"[Tool Call] create_email_draft: to {to_emails}, subject '{subject}'")
            try:
                draft_data = {
                    "to": to_emails,
                    "subject": subject,
                    "body": body
                }
                if reply_to_message_id:
                    draft_data["replyToMessageId"] = reply_to_message_id
                return self.mcp_client.create_draft(draft_data)
            except Exception as e:
                print(f"[Tool Error] create_email_draft: {e}")
                return {"error": str(e)}

        # Format threads content into a readable prompt
        threads_text = ""
        for i, thread in enumerate(threads):
            threads_text += f"\n--- Email Thread {i+1} ---\n"
            threads_text += f"Thread ID: {thread.get('id')}\n"
            messages = thread.get("messages", [])
            for msg in messages:
                sender = msg.get("fromAddress", msg.get("from", "Unknown Sender"))
                recipient = msg.get("toAddress", msg.get("to", "Unknown Recipient"))
                msg_date = msg.get("date", "Unknown Date")
                msg_subject = msg.get("subject", "No Subject")
                msg_body = msg.get("plaintextBody", msg.get("body", ""))
                msg_id = msg.get("id", "Unknown ID")
                
                threads_text += f"Message ID: {msg_id}\n"
                threads_text += f"From: {sender}\n"
                threads_text += f"To: {recipient}\n"
                threads_text += f"Date: {msg_date}\n"
                threads_text += f"Subject: {msg_subject}\n"
                threads_text += f"Body:\n{msg_body}\n"
            threads_text += "----------------------\n"

        current_time = datetime.datetime.now().isoformat()
        
        system_instruction = (
            "You are the 'Inbox Triage & Action Agent'. Your job is to process a batch of unread email threads "
            "and take actions using Gmail and Calendar tools.\n\n"
            "Triage Rules:\n"
            "1. Read the provided email threads.\n"
            "2. Identify the intent of each email:\n"
            "   a. MEETING REQUEST: If an email requests a meeting (e.g. 'Can we meet tomorrow at 3 PM?'), "
            "      first check availability around the requested time using `list_calendar_events` or `suggest_meeting_time`.\n"
            "      - If you are free: Schedule the meeting using `create_calendar_event` and draft a reply to the sender using `create_email_draft` confirming the event.\n"
            "      - If you are busy: Draft a reply using `create_email_draft` stating you are busy and suggesting alternative slots.\n"
            "   b. URGENT: If an email is urgent but not a meeting request, draft a reply using `create_email_draft` as appropriate.\n"
            "   c. FYI / NEWSLETTER: If an email is a newsletter, FYI, promotional, or does not require a response, "
            "      do NOT draft any reply or create any calendar events.\n"
            "3. Before outputting your final summary report, you must pass the entire generated markdown text "
            "   to the `sanitize_email_addresses` tool to redact all email addresses in one go to protect user privacy. "
            "   Also, use `analyze_urgency` on the email bodies as needed to evaluate urgency levels.\n"
            "4. After processing all threads, generate a single markdown summary.\n"
            "   The summary MUST start with the exact phrase: "
            "   'You had X emails. I drafted Y replies for urgent meetings, scheduled Z events, and the rest are newsletters/FYIs.' "
            "   Follow this with a clear breakdown table summarizing: Thread ID, Sender (use the sender's human-readable name or alias, e.g. 'Jane Doe' or 'Boss', rather than their raw email address so it remains visible after sanitization), Subject, Classification (Meeting Request / Urgent / Newsletter / FYI), Action Taken."
        )

        prompt = (
            f"Current local time: {current_time}\n"
            f"Here are the unread email threads to process:\n\n"
            f"{threads_text}\n"
            "Please triage them and execute any necessary calendar events and draft replies. "
            "When finished, output the final markdown summary."
        )

        # Build local MCP connection params
        server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_mcp_server.py")
        connection_params = StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=[server_path]
            )
        )
        local_mcp_toolset = McpToolset(connection_params=connection_params)

        tools_list = [
            list_calendar_events,
            suggest_meeting_time,
            create_calendar_event,
            create_email_draft,
            local_mcp_toolset
        ]

        async def _run_agent(model_name: str):
            adk_agent = Agent(
                model=model_name,
                name="triage_agent",
                instruction=system_instruction,
                tools=tools_list
            )
            session_service = InMemorySessionService()
            runner = Runner(
                app_name="inbox_triage_app",
                agent=adk_agent,
                session_service=session_service,
                auto_create_session=True
            )
            
            content = types.Content(role='user', parts=[types.Part(text=prompt)])
            final_response = ""
            
            async for event in runner.run_async(
                user_id="user_123",
                session_id="session_triage_run",
                new_message=content
            ):
                if hasattr(event, "is_final_response") and event.is_final_response():
                    if event.content and event.content.parts:
                        final_response = event.content.parts[0].text
            return final_response

        async def _run_with_fallback():
            primary_model = "gemini-2.5-flash"
            fallback_model = "gemini-3.1-flash-lite"
            try:
                print(f"[Agent] Attempting execution using primary model: {primary_model}...")
                return await _run_agent(primary_model)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str or "UNAVAILABLE" in err_str:
                    print(f"\n[Warning] Primary model '{primary_model}' is temporarily unavailable (Quota/503).")
                    print(f"[Warning] Falling back dynamically to: {fallback_model}...")
                    return await _run_agent(fallback_model)
                else:
                    raise e

        return asyncio.run(_run_with_fallback())
