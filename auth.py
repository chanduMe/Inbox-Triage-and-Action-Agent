import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import config

def get_credentials():
    """
    Retrieves OAuth 2.0 user credentials.
    Loads existing credentials from token.json if present.
    Refreshes them if expired, or runs a local web server flow to prompt the user
    to log in and authorize the requested scopes.
    """
    creds = None
    
    # Load previously stored user credentials if they exist
    if os.path.exists(config.TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
        except Exception as e:
            print(f"Error loading existing token.json: {e}. Re-authenticating.")
            creds = None

    # If there are no valid credentials, handle authentication/refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired Google credentials...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh token: {e}. Initiating fresh login flow.")
                creds = None
                
        if not creds:
            print("Google credentials not found or invalid. Initiating OAuth 2.0 flow...")
            if not os.path.exists(config.CREDENTIALS_FILE):
                error_msg = (
                    f"\n[ERROR] Credentials file '{config.CREDENTIALS_FILE}' is missing.\n"
                    "Please perform the following steps:\n"
                    "1. Go to Google Cloud Console (https://console.cloud.google.com)\n"
                    "2. Create a project and enable 'Gmail API' and 'Google Calendar API'\n"
                    "3. Configure OAuth Consent Screen (internal or external test users)\n"
                    "4. Create OAuth Client ID (type: Web Application or Desktop)\n"
                    f"   - Add Authorized Redirect URI: http://localhost:{config.REDIRECT_PORT}/\n"
                    "5. Download the JSON credentials file, rename it to 'credentials.json' and place it in the workspace root."
                )
                raise FileNotFoundError(error_msg)
                
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.CREDENTIALS_FILE), config.SCOPES
            )
            # Run local server to capture the code
            creds = flow.run_local_server(port=config.REDIRECT_PORT)
            
        # Save credentials for the next run
        print(f"Saving new credentials to {config.TOKEN_FILE}...")
        with open(config.TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds

if __name__ == "__main__":
    # Test credentials retrieval
    try:
        credentials = get_credentials()
        print("Successfully authenticated Google Workspace!")
        print("Token validity:", credentials.valid)
    except Exception as e:
        print("Failed to authenticate:", e)
