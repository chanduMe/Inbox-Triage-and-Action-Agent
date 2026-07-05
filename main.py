import os
import sys
from dotenv import load_dotenv
import auth
import config
from mcp_client import WorkspaceMCPClient
from agent import TriageAgent

def main():
    # Load environment variables (.env file)
    load_dotenv(override=True)
    
    # Ensure GEMINI_API_KEY is configured
    if not os.environ.get("GEMINI_API_KEY"):
        print("[ERROR] GEMINI_API_KEY environment variable is not set.")
        print("Please create a '.env' file in the workspace root containing:")
        print("GEMINI_API_KEY=your_gemini_api_key_here")
        sys.exit(1)

    print("Authenticating with Google Workspace...")
    try:
        creds = auth.get_credentials()
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        sys.exit(1)
        
    # Initialize the Workspace MCP Client
    mcp_client = WorkspaceMCPClient(creds)
    
    print("Retrieving the last 5 unread email threads in the Primary category...")
    try:
        # Search unread threads
        search_res = mcp_client.search_threads("is:unread category:primary", max_results=5)
        
        # Structure may be directly list of threads or dict with 'threads' key
        threads = []
        if isinstance(search_res, dict):
            threads = search_res.get("threads", [])
        elif isinstance(search_res, list):
            threads = search_res
            
        if not threads:
            print("\nNo unread email threads found!")
            print("You had 0 emails. No actions were taken.")
            sys.exit(0)
            
        # Limit to last 5
        threads = threads[:5]
        print(f"Fetching details for the latest {len(threads)} unread threads...")
        detailed_threads = []
        for i, thread in enumerate(threads):
            thread_id = thread.get("id")
            if thread_id:
                print(f"[{i+1}/{len(threads)}] Fetching thread details for {thread_id}...")
                detailed_thread = mcp_client.get_thread(thread_id)
                detailed_threads.append(detailed_thread)
                
    except Exception as e:
        print(f"[ERROR] Failed to fetch email threads: {e}")
        sys.exit(1)
        
    print("\nRunning Triage Agent ReAct Loop...")
    try:
        agent = TriageAgent(mcp_client)
        summary = agent.run_triage(detailed_threads)
        
        print("\n=== Inbox Triage & Action Report ===")
        print(summary)
        print("====================================")
        
    except Exception as e:
        print(f"[ERROR] Agent execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
