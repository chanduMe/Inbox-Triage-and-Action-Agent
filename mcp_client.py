import json
import httpx
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
import config

class WorkspaceMCPClient:
    def __init__(self, credentials):
        self.credentials = credentials

    def _get_headers(self):
        """
        Ensure credentials are valid (refreshes if necessary) and return OAuth authorization headers.
        """
        if not self.credentials.valid:
            print("Refreshing access token for API request...")
            self.credentials.refresh(Request())
            # Save the refreshed token
            with open(config.TOKEN_FILE, "w") as token_file:
                token_file.write(self.credentials.to_json())
        
        return {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _parse_mcp_result(self, result: dict):
        """
        MCP tools return standard content blocks: {"content": [{"type": "text", "text": "..."}]}.
        This helper parses the string inside 'text' as a JSON dict (or returns the raw string/dict if not JSON).
        """
        if not result:
            return {}
        
        # Check if the MCP server returned an error indicator
        if result.get("isError"):
            content = result.get("content", [])
            err_text = content[0].get("text", "") if content else "Unknown MCP Error"
            raise PermissionError(f"MCP Server returned error: {err_text}")

        content = result.get("content", [])
        if not content:
            return result
        
        first_item = content[0]
        if first_item.get("type") == "text":
            text = first_item.get("text", "")
            # Check for permission strings
            if "does not have permission" in text or "Forbidden" in text:
                raise PermissionError(f"MCP Server Permission Error: {text}")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return result

    def _format_rfc3339(self, dt_str: str) -> str:
        """
        Safely formats a datetime string for Google REST APIs by ensuring timezone.
        """
        if not dt_str:
            return dt_str
        if dt_str.endswith("Z"):
            return dt_str
        t_index = dt_str.find("T")
        if t_index != -1:
            suffix = dt_str[t_index:]
            if "+" in suffix or "-" in suffix:
                return dt_str
        return dt_str + "Z"


    def call_tool(self, server_url: str, tool_name: str, arguments: dict = None) -> dict:
        """
        Invokes a tool on an MCP HTTP server using JSON-RPC 2.0.
        """
        if arguments is None:
            arguments = {}

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }

        headers = self._get_headers()
        
        with httpx.Client(timeout=30.0) as client:
            try:
                response = client.post(server_url, json=payload, headers=headers)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    raise PermissionError(f"MCP Server HTTP 403: {e.response.text}")
                raise e
            
            res_data = response.json()
            if "error" in res_data:
                raise Exception(f"MCP server error: {res_data['error']}")
                
            return res_data.get("result", {})

    def list_tools(self, server_url: str) -> list:
        """
        Lists tools supported by the remote MCP server.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }

        headers = self._get_headers()
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(server_url, json=payload, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            
            if "error" in res_data:
                raise Exception(f"MCP server error: {res_data['error']}")
                
            return res_data.get("result", {}).get("tools", [])

    # =========================================================================
    # --- Fallback REST API Helpers ---
    # =========================================================================

    def _get_gmail_header(self, headers: list, name: str) -> str:
        for h in headers:
            if h.get("name", "").lower() == name.lower():
                return h.get("value", "")
        return ""

    def _get_gmail_plaintext_body(self, payload: dict) -> str:
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
        
        parts = payload.get("parts", [])
        for part in parts:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            elif "parts" in part:
                body = self._get_gmail_plaintext_body(part)
                if body:
                    return body
        return ""

    # =========================================================================
    # --- Gmail MCP & REST API Helpers ---
    # =========================================================================
    
    def search_threads(self, query: str, max_results: int = 20) -> dict:
        """
        Search for threads matching a Gmail search query (e.g. 'is:unread').
        """
        try:
            raw_res = self.call_tool(config.GMAIL_MCP_URL, "search_threads", {"query": query, "pageSize": max_results})
            return self._parse_mcp_result(raw_res)
        except Exception as e:
            print(f"[REST Fallback] Gmail MCP search_threads failed: {e}. Executing REST call...")
            headers = self._get_headers()
            url = "https://gmail.googleapis.com/gmail/v1/users/me/threads"
            params = {
                "q": query,
                "maxResults": max_results
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, params=params, headers=headers)
                res.raise_for_status()
                return res.json()

    def get_thread(self, thread_id: str) -> dict:
        """
        Fetch details and message content for a thread.
        """
        try:
            raw_res = self.call_tool(config.GMAIL_MCP_URL, "get_thread", {"threadId": thread_id})
            return self._parse_mcp_result(raw_res)
        except Exception as e:
            print(f"[REST Fallback] Gmail MCP get_thread failed: {e}. Executing direct REST API call...")
            headers = self._get_headers()
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, headers=headers)
                res.raise_for_status()
                raw_thread = res.json()
                
                # Format standard REST thread to match the schema expected by agent.py
                mcp_formatted_messages = []
                for msg in raw_thread.get("messages", []):
                    headers_list = msg.get("payload", {}).get("headers", [])
                    mcp_formatted_messages.append({
                        "id": msg.get("id"),
                        "from": self._get_gmail_header(headers_list, "From"),
                        "to": self._get_gmail_header(headers_list, "To"),
                        "date": self._get_gmail_header(headers_list, "Date"),
                        "subject": self._get_gmail_header(headers_list, "Subject"),
                        "plaintextBody": self._get_gmail_plaintext_body(msg.get("payload", {}))
                    })
                return {"id": thread_id, "messages": mcp_formatted_messages}

    def create_draft(self, draft: dict) -> dict:
        """
        Create a draft reply email.
        Accepts MCP structure: {'to': [...], 'subject': '...', 'body': '...', 'replyToMessageId': '...'}
        """
        try:
            raw_res = self.call_tool(config.GMAIL_MCP_URL, "create_draft", {"draft": draft})
            return self._parse_mcp_result(raw_res)
        except Exception as e:
            print(f"[REST Fallback] Gmail MCP create_draft failed: {e}. Executing direct REST API call...")
            headers = self._get_headers()
            
            # Format raw MIME message
            msg = EmailMessage()
            msg.set_content(draft.get("body", ""))
            msg["To"] = ", ".join(draft.get("to", []))
            msg["Subject"] = draft.get("subject", "No Subject")
            
            reply_to = draft.get("replyToMessageId")
            if reply_to:
                msg["In-Reply-To"] = reply_to
                msg["References"] = reply_to

            raw_bytes = msg.as_bytes()
            raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
            
            payload = {
                "message": {
                    "raw": raw_b64
                }
            }
            # Optional: link to a thread
            # If draft has a threadId, we can add it to the message object
            # Note: We need threadId from raw thread metadata
            
            url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                return res.json()

    # =========================================================================
    # --- Calendar MCP & REST API Helpers ---
    # =========================================================================

    def list_events(self, start_time: str, end_time: str, page_size: int = 10) -> dict:
        """
        List calendar events between startTime and endTime (ISO 8601).
        """
        try:
            raw_res = self.call_tool(
                config.CALENDAR_MCP_URL, 
                "list_events", 
                {"startTime": start_time, "endTime": end_time, "pageSize": page_size}
            )
            return self._parse_mcp_result(raw_res)
        except Exception as e:
            print(f"[REST Fallback] Calendar MCP list_events failed: {e}. Executing direct REST API call...")
            headers = self._get_headers()
            time_min = self._format_rfc3339(start_time)
            time_max = self._format_rfc3339(end_time)
            
            url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
            params = {
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": page_size
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, params=params, headers=headers)
                res.raise_for_status()
                data = res.json()
                return {"events": data.get("items", [])}

    def suggest_time(self, attendee_emails: list, start_time: str, end_time: str, duration_minutes: int = 30) -> dict:
        """
        Suggest open slots for specified attendees.
        If MCP fails, uses list_events fallback to check primary calendar slots locally.
        """
        try:
            raw_res = self.call_tool(
                config.CALENDAR_MCP_URL,
                "suggest_time",
                {
                    "attendeeEmails": attendee_emails,
                    "startTime": start_time,
                    "endTime": end_time,
                    "durationMinutes": duration_minutes
                }
            )
            return self._parse_mcp_result(raw_res)
        except Exception as e:
            print(f"[REST Fallback] Calendar MCP suggest_time failed: {e}. Falling back to local slot calculation...")
            # Fallback local logic using list_events
            events_res = self.list_events(start_time, end_time, page_size=100)
            events = events_res.get("events", [])
            
            # Extract busy periods
            import datetime
            busy_periods = []
            for ev in events:
                start_ev = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date"))
                end_ev = ev.get("end", {}).get("dateTime", ev.get("end", {}).get("date"))
                if start_ev and end_ev:
                    # Parse to datetime
                    # Simple parse assuming ISO format
                    dt_start = datetime.datetime.fromisoformat(start_ev.replace("Z", "+00:00"))
                    dt_end = datetime.datetime.fromisoformat(end_ev.replace("Z", "+00:00"))
                    busy_periods.append((dt_start, dt_end))
            
            # Sort busy periods
            busy_periods.sort(key=lambda x: x[0])
            
            # Search open slots
            dt_start_search = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            dt_end_search = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            
            suggested_slots = []
            current_slot_start = dt_start_search
            
            for busy_start, busy_end in busy_periods:
                if current_slot_start + datetime.timedelta(minutes=duration_minutes) <= busy_start:
                    # Found free slot before next busy period
                    suggested_slots.append({
                        "startTime": current_slot_start.isoformat(),
                        "endTime": (current_slot_start + datetime.timedelta(minutes=duration_minutes)).isoformat()
                    })
                # Move pointer past the busy period
                if busy_end > current_slot_start:
                    current_slot_start = busy_end
                    
            # Check if there is space at the end of the search range
            if current_slot_start + datetime.timedelta(minutes=duration_minutes) <= dt_end_search:
                suggested_slots.append({
                    "startTime": current_slot_start.isoformat(),
                    "endTime": (current_slot_start + datetime.timedelta(minutes=duration_minutes)).isoformat()
                })
                
            return {"timeSlots": suggested_slots[:5]}

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = None) -> dict:
        """
        Schedule an event on the user's primary calendar.
        """
        try:
            args = {
                "summary": summary,
                "startTime": start_time,
                "endTime": end_time
            }
            if description:
                args["description"] = description
            raw_res = self.call_tool(config.CALENDAR_MCP_URL, "create_event", args)
            return self._parse_mcp_result(raw_res)
        except Exception as e:
            print(f"[REST Fallback] Calendar MCP create_event failed: {e}. Executing direct REST API call...")
            headers = self._get_headers()
            
            # Format standard Calendar API event body
            payload = {
                "summary": summary,
                "description": description or "",
                "start": {"dateTime": self._format_rfc3339(start_time)},
                "end": {"dateTime": self._format_rfc3339(end_time)}
            }
            
            url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                return res.json()
