---
name: inbox-triage-agent
description: Automatically triages Gmail inbox unread emails, checks Calendar availability for meeting requests, drafts replies, schedules calendar events, and outputs a summary.
---

# Inbox Triage & Action Skill

This skill teaches the agent how to automate email triage and schedule meetings using Google Workspace APIs or MCP servers.

## Workflow

When the user asks to "run email triage", "triage my inbox", or when triggered by a background schedule, follow these steps:

### Step 1: Detect Available Tools
Check if the IDE has direct registered MCP tools for Gmail (`search_threads`, `get_thread`, `create_draft`) and Calendar (`list_events`, `suggest_time`, `create_event`).

*   **Case A: Direct MCP Tools are available in IDE context**
    Proceed with Step 2 (Native Triage).
*   **Case B: Direct MCP Tools are NOT available**
    Fallback to Step 3 (Orchestrator Execution).

---

### Step 2: Native Triage (Using IDE MCP Tools)

1.  **Retrieve Emails**:
    Call `search_threads` with query `"is:unread category:primary"` and `pageSize=20`.
    *   If no threads are returned, report: "You had 0 emails. No actions were taken." and stop.
    *   Otherwise, for each returned thread, call `get_thread` with `threadId` to fetch its full content.
2.  **Analyze and Process Threads**:
    For each thread, inspect the messages:
    *   **Meeting Request**: If the sender requests a meeting (e.g. "Can we meet tomorrow at 3 PM?"):
        *   Determine the requested time range.
        *   Call `list_events` or `suggest_time` on the user's primary calendar to check availability.
        *   **If Free**: Call `create_event` to block the slot, then call `create_draft` to draft a confirmation email to the sender.
        *   **If Busy**: Call `create_draft` to draft a reply stating you have a conflict and suggest alternative open slots.
    *   **Urgent Request (Non-Meeting)**: Call `create_draft` to draft an appropriate response.
    *   **FYI / Newsletter**: Take no action.
3.  **Generate Report**:
    Output a single markdown summary starting with:
    `You had X emails. I drafted Y replies for urgent meetings, scheduled Z events, and the rest are newsletters/FYIs.`
    Include a detailed table breakdown of the processed threads.

---

### Step 3: Orchestrator Execution (Fallback)

1.  **Check Local Virtual Environment**:
    Verify that the virtual environment `.venv` exists in the workspace.
2.  **Check API Credentials**:
    Verify that `credentials.json` is present in the workspace root. If missing, explain the GCP setup instructions to the user.
3.  **Run Dashboard Backend or CLI**:
    Propose and run the dashboard server:
    ```bash
    .venv/bin/python3 app.py
    ```
    Alternatively, run the simulated CLI:
    ```bash
    .venv/bin/python3 run_mocked_simulation.py
    ```
4.  **Display Report**:
    Present the printed output and markdown summary directly in the chat.
