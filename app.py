import os
import sys
import io
import asyncio
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import contextmanager
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

# Import Mock and live clients
from run_mocked_simulation import MockWorkspaceMCPClient
from agent import TriageAgent
import auth
from mcp_client import WorkspaceMCPClient

app = FastAPI(title="Concierge Triage Agent Dashboard")

@contextmanager
def capture_stdout():
    old_out = sys.stdout
    new_out = io.StringIO()
    sys.stdout = new_out
    try:
        yield new_out
    finally:
        sys.stdout = old_out

@app.get("/api/run-triage")
def run_triage_api(mode: str = Query("mock", pattern="^(mock|live)$")):
    logs = []
    summary = ""
    success = True
    error_msg = ""
    
    with capture_stdout() as captured:
        try:
            if mode == "mock":
                print("[API] Running in SIMULATION (Mock) mode...")
                mock_client = MockWorkspaceMCPClient()
                search_res = mock_client.search_threads("is:unread")
                threads = [mock_client.get_thread(t["id"]) for t in search_res.get("threads", [])]
                agent = TriageAgent(mock_client)
                summary = agent.run_triage(threads)
                print("[API] Simulation run completed successfully.")
            else:
                print("[API] Running in LIVE mode...")
                if not os.environ.get("GEMINI_API_KEY"):
                    raise ValueError("GEMINI_API_KEY environment variable is not set in .env.")
                
                # Live Workspace Auth
                creds = auth.get_credentials()
                mcp_client = WorkspaceMCPClient(creds)
                
                print("[API] Searching unread email threads...")
                search_res = mcp_client.search_threads("is:unread category:primary", max_results=5)
                threads = []
                if isinstance(search_res, dict):
                    threads = search_res.get("threads", [])
                elif isinstance(search_res, list):
                    threads = search_res
                
                if not threads:
                    print("[API] No unread threads found!")
                    summary = "You had 0 emails. No actions were taken."
                else:
                    threads = threads[:5]
                    print(f"[API] Fetching details for the latest {len(threads)} unread threads...")
                    detailed_threads = []
                    for t in threads:
                        tid = t.get("id")
                        if tid:
                            detailed_threads.append(mcp_client.get_thread(tid))
                    
                    print("[API] Initializing ADK Agent and starting triage...")
                    agent = TriageAgent(mcp_client)
                    summary = agent.run_triage(detailed_threads)
                print("[API] Live triage completed successfully.")
                
        except Exception as e:
            success = False
            error_msg = str(e)
            print(f"[API ERROR] Execution failed: {e}")
            import traceback
            traceback.print_exc()

    logs = captured.getvalue().strip().split("\n")
    logs = [l for l in logs if l.strip()]

    return JSONResponse(content={
        "success": success,
        "mode": mode,
        "logs": logs,
        "summary": summary,
        "error": error_msg
    })

# Serve the static files
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
