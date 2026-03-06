# ============================================================
# backend/main.py
# ============================================================
# Updated with proper OAuth redirect flow for web users.
# Instead of a desktop popup, users get redirected to Google,
# log in, and get sent back to our app automatically.
# ============================================================

import os
import sys
import shutil
import uuid
import json
from urllib.parse import quote

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.reader import extract_text_from_screenshot
from src.parser import parse_schedule


# --- SETUP ---

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "https://snapshot-cxv35vipn-grantdibiases-projects.vercel.app",
        "https://snapshot-5qjezf9yo-grantdibiases-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# We store the user's credentials in memory temporarily.
# In a real production app you'd store these in a database.
# In this demo it is fine for short-lived sessions.
user_credentials = {}

# Directory to persist session credentials
SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

def save_session(session_id: str, creds_data: dict, events: list = None):
    """Save credentials and optionally events to disk so they survive backend restart."""
    try:
        data_to_save = {"credentials": creds_data}
        if events:
            data_to_save["events"] = events
            
        with open(os.path.join(SESSIONS_DIR, f"{session_id}.json"), "w") as f:
            json.dump(data_to_save, f)
        print(f"[SESSION] Saved session {session_id} to disk")
    except Exception as e:
        print(f"[SESSION] Warning: Could not save session to disk: {e}")

def load_session(session_id: str) -> dict:
    """Load credentials from disk if they exist."""
    try:
        path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            
            # Handle both old format (just creds) and new format (creds + events)
            creds_data = data.get("credentials") if isinstance(data, dict) and "credentials" in data else data
            print(f"[SESSION] Loaded session {session_id} from disk")
            return creds_data
    except Exception as e:
        print(f"[SESSION] Warning: Could not load session from disk: {e}")
    return None


# --- DATA MODELS ---

class Event(BaseModel):
    title: str
    type: Optional[str] = None
    days: Optional[List[str]] = []
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    professor: Optional[str] = None
    semester_start: Optional[str] = None
    semester_end: Optional[str] = None


class ConfirmRequest(BaseModel):
    events: List[Event]
    session_id: str
    # session_id identifies which user's credentials to use
    # when creating calendar events


# --- ENDPOINTS ---

@app.get("/")
def root():
    return {"status": "Snapshot API is running!"}


@app.post("/upload")
async def upload_screenshots(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    saved_paths = []

    try:
        for file in files:
            unique_name = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_paths.append(file_path)

        all_raw_text = ""
        for path in saved_paths:
            raw_text = extract_text_from_screenshot(path)
            all_raw_text += raw_text + "\n\n"

        events = parse_schedule(all_raw_text)

        return JSONResponse(content={"events": events})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for path in saved_paths:
            if os.path.exists(path):
                os.remove(path)


@app.get("/auth/google")
async def google_auth(request: Request):
    # --------------------------------------------------------
    # Step 1 of OAuth — generate the Google login URL and
    # send it back to the frontend so it can redirect the user.
    # --------------------------------------------------------
    
    # Get the client's origin (hostname:port) to use in redirect
    # This allows the app to work from localhost OR external IP
    client_origin = request.headers.get("origin", "http://localhost:3000")
    print(f"[AUTH] Client origin: {client_origin}")
    
    # Extract the hostname/port from origin and replace with backend port
    # Works for any frontend port (3000, 3003, etc.)
    from urllib.parse import urlparse
    parsed = urlparse(client_origin)
    hostname = parsed.hostname or "localhost"
    callback_url = f"{parsed.scheme}://{hostname}:8000/auth/callback"
    print(f"[AUTH] Callback URL: {callback_url}")
    
    import json
    credentials_info = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
    Flow.from_client_config(
        credentials_info,
        scopes=SCOPES,
        redirect_uri=...
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    # Save the Flow object keyed by state so we can complete the
    # OAuth handshake in the callback (PKCE requires the same flow).
    user_credentials[state] = {"flow": flow}

    return JSONResponse(content={"auth_url": auth_url, "state": state})


@app.get("/auth/callback")
async def google_callback(code: str, state: str, request: Request):
    # --------------------------------------------------------
    # Step 2 of OAuth — Google redirects the user back here
    # after they log in. We exchange the code for credentials.
    # --------------------------------------------------------
    try:
        # Get the origin to redirect back to the same place the user came from
        client_origin = request.headers.get("origin", "http://localhost:3000")
        print(f"[CALLBACK] Client origin: {client_origin}")
        print(f"[CALLBACK] Received code={code[:20]}..., state={state[:20]}...")
        print(f"[CALLBACK] Available states in memory: {list(user_credentials.keys())[:3]}...")
        
        if state not in user_credentials or "flow" not in user_credentials[state]:
            raise Exception("Missing OAuth state. Please restart the login flow.")

        print(f"[CALLBACK] Found flow in memory, exchanging code for token...")
        flow = user_credentials[state]["flow"]
        flow.fetch_token(code=code)
        print(f"[CALLBACK] ✓ Token exchange successful!")

        creds = flow.credentials

        session_id = str(uuid.uuid4())
        print(f"[CALLBACK] Created session_id={session_id}")

        user_credentials[session_id] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else [],
        }

        # Save to disk so it survives backend restart
        save_session(session_id, user_credentials[session_id])

        # Clean up the temporary flow state entry
        user_credentials.pop(state, None)
        print(f"[CALLBACK] ✓ Credentials stored in memory and on disk")
        print(f"[CALLBACK] Redirecting to {client_origin}/confirm with session_id={session_id}")

        # Redirect back to the frontend with the session ID
        return RedirectResponse(
            url=f"https://snapshot-5qjezf9yo-grantdibiases-projects.vercel.app/confirm?session_id={session_id}&auth=success"
        )

    except Exception as e:
        print(f"[CALLBACK] ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        return RedirectResponse(
            url=f"https://snapshot-5qjezf9yo-grantdibiases-projects.vercel.app/confirm?auth=error&message={str(e)}"
        )


@app.post("/confirm")
async def confirm_events(request: ConfirmRequest):
    # --------------------------------------------------------
    # Creates all events in the user's Google Calendar.
    # Uses the session_id to find their credentials.
    # --------------------------------------------------------
    try:
        print(f"\n[CONFIRM] Received confirm request with session_id={request.session_id[:20]}...")
        print(f"[CONFIRM] Available sessions in memory: {list(user_credentials.keys())[:3]}...")
        print(f"[CONFIRM] Event count: {len(request.events)}")
        
        # Validate that there are events to create
        if len(request.events) == 0:
            raise HTTPException(
                status_code=400,
                detail="No events to add! Please upload screenshots first."
            )
        
        # Try to find credentials in memory first
        creds_data = user_credentials.get(request.session_id)
        
        # If not in memory, try to load from disk (in case backend restarted)
        if not creds_data:
            print(f"[CONFIRM] Session not in memory, trying to load from disk...")
            creds_data = load_session(request.session_id)
        
        if not creds_data:
            print(f"[CONFIRM] ✗ Session not found! Available: {list(user_credentials.keys())}")
            raise HTTPException(
                status_code=401,
                detail="Not authenticated. Please connect Google Calendar first."
            )

        print(f"[CONFIRM] ✓ Session found, reconstructing credentials...")
        creds = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data["refresh_token"],
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"],
        )

        from src.calendar_builder import create_calendar_events_with_creds
        print(f"[CONFIRM] Calling create_calendar_events_with_creds...")
        create_calendar_events_with_creds(
            [event.dict() for event in request.events],
            creds
        )

        print(f"[CONFIRM] ✓ Events created successfully!")
        return JSONResponse(content={"status": "success"})

    except Exception as e:
        error_msg = str(e)
        print(f"[CONFIRM] ✗ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": error_msg}
        )


# --- TEST ENDPOINT (for debugging without OAuth) ---

@app.post("/test/confirm")
async def test_confirm_events(request: ConfirmRequest):
    # --------------------------------------------------------
    # DEBUG ENDPOINT: Test event creation without OAuth flow.
    # Uses the token.json file directly.
    # Remove this endpoint in production!
    # --------------------------------------------------------
    try:
        if not os.path.exists("token.json"):
            raise Exception("token.json not found. Please authenticate first.")

        with open("token.json", "r") as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", SCOPES),
        )

        from src.calendar_builder import create_calendar_events_with_creds
        create_calendar_events_with_creds(
            [event.dict() for event in request.events],
            creds
        )

        return JSONResponse(content={"status": "success"})

    except Exception as e:
        print(f"TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)}
        )
