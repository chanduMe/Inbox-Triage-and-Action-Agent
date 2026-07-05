# Inbox Triage & Action Agent (Kaggle Capstone Submission)

An agentic web application and workspace automator built using Google's official **Agent Development Kit (ADK)** and the **Model Context Protocol (MCP)**. It automatically triages unread Gmail threads, evaluates schedule availability, creates Google Calendar events, and drafts formatted email responses with privacy redaction safeguards.

This project is submitted under the **Concierge track** of the *AI Agents: Intensive Vibe Coding Capstone Project*.

---

## Technical Architecture & Capstone Highlights

*   **Google Agent Development Kit (ADK)**: Refactored core agent reasoning in `agent.py` to use ADK's native `Agent` and `Runner` framework, orchestrating local and remote tool calls dynamically.
*   **Custom Local MCP Server (`local_mcp_server.py`)**: Built using `fastmcp` to expose security, privacy, and heuristic triage tools. Exposes `sanitize_email_addresses` to redact email strings from logs and reports for user privacy, and `analyze_urgency` to assess message severity.
*   **Self-Healing Model Fallback**: Implemented dynamic error-handling in `agent.py`. The agent attempts to use the primary model (`gemini-2.5-flash`) by default, but if it catches a 429 quota block or a 503 unavailable error, it automatically falls back to `gemini-3.1-flash-lite`, ensuring high availability and self-healing resilience.
*   **Category-based Inbox Filtering (Scope Minimization)**: The search query is constrained specifically to `"is:unread category:primary"`. This restricts the agent to triaging only the user's primary inbox messages, automatically ignoring clutter in Promotions, Social, and Updates tabs, thereby protecting user privacy and reducing LLM token consumption.
*   **REST API Fallback Client**: If remote Google Workspace MCP endpoints return permission blocks (HTTP 403) due to Developer Preview restrictions, the client gracefully degrade-redirects commands to standard Google REST endpoints on the fly.
*   **Interactive Web UI Dashboard**: A sleek, dark-themed glassmorphic developer dashboard built using FastAPI and Vanilla CSS. Features real-time execution log visualization, simulation/live toggles, metrics trackers, and a formatted Markdown report renderer.

---

## File Structure

*   `app.py`: FastAPI server serving the Web UI Dashboard and run endpoints.
*   `local_mcp_server.py`: Custom local Model Context Protocol (MCP) server exposing utility tools.
*   `static/`: Directory containing frontend code:
    *   `index.html`: Dashboard structure with font integrations.
    *   `style.css`: Gorgeous glassmorphism theme, layout styling, and animations.
    *   `app.js`: Backend fetch routines, terminal log filters, and metrics counting.
*   `requirements.txt`: Python package dependencies (including `google-adk`, `fastapi`, `uvicorn`, `fastmcp`, and `mcp`).
*   `config.py`: Core configurations (API scopes, Gmail/Calendar MCP URLs).
*   `auth.py`: Handles OAuth 2.0 flow and credentials refresh.
*   `mcp_client.py`: Decoupled Workspace MCP Client wrapper with REST Fallback.
*   `agent.py`: ADK Agent loop registering Workspace adapter functions and the local MCP toolset.
*   `main.py`: Synchronous CLI orchestrator.
*   `test_agent.py`: Unit test suite.
*   `run_mocked_simulation.py`: Simulation runner that executes the real ADK agent on mock Gmail/Calendar data.
*   `docs/`: Documentation folder containing:
    *   `DEVELOPMENT_MANIFESTO.md`: Technical development principles.
    *   `concepts_reference.md`: Extended troubleshooting and architectural concepts.
    *   `INTERVIEW_GUIDE.md`: Deep-dive interview walkthrough script.
    *   `ALL_IN_ONE_GUIDE.md`: Consolidated print-ready guide.
*   `.agents/skills/inbox-triage-agent/SKILL.md`: IDE Agent Skill for timers and scheduling triggers.

---

## Setup & Installation

### 1. Initialize Python Environment
Create a virtual environment and install the required packages:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key
Create a `.env` file at the root of the project and add your Gemini API Key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Google Workspace Credentials (Optional for Live Mode)
To run the agent in Live Mode against your real Gmail/Calendar:
1. Go to the [Google Cloud Console](https://console.cloud.google.com).
2. Create a project and enable the **Gmail API** and **Google Calendar API**.
3. Configure the OAuth Consent Screen and add your email to the **Test Users** list.
4. Create OAuth Client Credentials (type: **Desktop Application**).
5. Download the JSON file, rename it to `credentials.json`, and place it in the workspace root.

---

## How to Run & Verify

### 1. Run the Web Dashboard
Launch the FastAPI development server:
```bash
python3 app.py
```
Then, open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

From the dashboard, you can:
*   Toggle between **Simulation Mode** (mocked Workspace data) and **Live Sync** (live Gmail/Calendar connection).
*   Click **Run Triage Agent** to watch the real-time execution progress, monitor tool calls, and view the final generated report.

### 2. Run Simulated Triage CLI
To run the real ADK agent inside the terminal using mock threads:
```bash
python3 run_mocked_simulation.py
```

### 3. Run Live Triage CLI
To execute the live triage sequence via the terminal:
```bash
python3 main.py
```
*(On first execution, a browser tab will open for secure Google OAuth authorization. Mark the scopes checkbox and consent to continue).*

### 4. Run Unit Tests
Verify parsing layer sanity:
```bash
python3 -m unittest test_agent.py
```
