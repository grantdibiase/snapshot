# ============================================================
# backend/main.py
# ============================================================
# Updated with proper OAuth redirect flow for web users.
# Instead of a desktop popup, users get redirected to Google,
# log in, and get sent back to our app automatically.
# ============================================================

import os
import sys
import uuid
import json
import logging
import tempfile
import time
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from src.reader import extract_text_from_screenshot
from src.parser import parse_schedule
from src.event_types import event_type
from datetime import date


# --- SETUP ---

app = FastAPI()

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://snapshot-ecru-six.vercel.app",
).rstrip("/")
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://snapshot-backend-j49i.onrender.com",
).rstrip("/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "https://snapshot-cxv35vipn-grantdibiases-projects.vercel.app",
        "https://snapshot-ecru-six.vercel.app",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = str(PROJECT_ROOT / "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# We store the user's credentials in memory temporarily.
# In a real production app you'd store these in a database.
# In this demo it is fine for short-lived sessions.
user_credentials = {}

# Directory to persist session credentials
SESSIONS_DIR = os.getenv("SESSIONS_DIR", str(PROJECT_ROOT / "sessions"))
os.makedirs(SESSIONS_DIR, exist_ok=True)

def save_session(session_id: str, creds_data: dict, events: list = None):
    """Save credentials and optionally events to disk so they survive backend restart."""
    try:
        data_to_save = {"credentials": creds_data}
        if events:
            data_to_save["events"] = events
            
        with open(os.path.join(SESSIONS_DIR, f"{session_id}.json"), "w") as f:
            json.dump(data_to_save, f)
    except Exception as e:
        print(f"[SESSION] Warning: Could not save session to disk: {e}")

def load_session(session_id: str) -> dict:
    """Load credentials from disk if they exist."""
    try:
        if str(uuid.UUID(session_id)) != session_id:
            return None
        path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            
            # Handle both old format (just creds) and new format (creds + events)
            creds_data = data.get("credentials") if isinstance(data, dict) and "credentials" in data else data
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
def upload_screenshots(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Upload at most 10 screenshots.")
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="Screenshot processing is not configured.")

    saved_paths = []

    try:
        for file in files:
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg"}:
                raise HTTPException(status_code=415, detail="Upload PNG or JPEG screenshots.")
            with tempfile.NamedTemporaryFile(dir=UPLOAD_DIR, suffix=suffix, delete=False) as buffer:
                saved_paths.append(buffer.name)
                size = 0
                while chunk := file.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 10 * 1024 * 1024:
                        raise HTTPException(status_code=413, detail="Each screenshot must be 10 MB or smaller.")
                    buffer.write(chunk)
                if size == 0:
                    raise HTTPException(status_code=400, detail="Screenshots must not be empty.")

        all_raw_text = ""
        for path in saved_paths:
            raw_text = extract_text_from_screenshot(path)
            all_raw_text += raw_text + "\n\n"

        events = parse_schedule(all_raw_text)
        for event in events:
            event["type"] = event_type(event)

        return JSONResponse(content={"events": events})

    except HTTPException:
        raise
    except Exception:
        logger.exception("Screenshot processing failed")
        raise HTTPException(status_code=502, detail="Unable to process screenshots. Please try again.")

    finally:
        for path in saved_paths:
            if os.path.exists(path):
                os.remove(path)


@app.get("/auth/google")
def google_auth(request: Request):
    # --------------------------------------------------------
    # Step 1 of OAuth — generate the Google login URL and
    # send it back to the frontend so it can redirect the user.
    # --------------------------------------------------------
    
    # Remember the frontend for the callback; Google will not send the
    # browser's Origin header when it redirects back to this API.
    client_origin = request.headers.get("origin", FRONTEND_URL).rstrip("/")
    if client_origin not in {FRONTEND_URL, "http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003"}:
        raise HTTPException(status_code=403, detail="Frontend origin is not allowed")

    callback_url = f"{BACKEND_URL}/auth/callback"
    print(f"[AUTH] Callback URL: {callback_url}")

    credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise HTTPException(status_code=500, detail="GOOGLE_CREDENTIALS_JSON is not configured")

    credentials_info = json.loads(credentials_json)
    flow = Flow.from_client_config(
        credentials_info,
        scopes=SCOPES,
        redirect_uri=callback_url,
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    # Save the Flow object keyed by state so we can complete the
    # OAuth handshake in the callback (PKCE requires the same flow).
    now = time.monotonic()
    for key, value in list(user_credentials.items()):
        if "flow" in value and now - value.get("created_at", 0) > 600:
            user_credentials.pop(key, None)
    user_credentials[state] = {"flow": flow, "client_origin": client_origin, "created_at": now}

    return JSONResponse(content={"auth_url": auth_url, "state": state})


@app.get("/auth/callback")
def google_callback(request: Request, state: str = "", code: str = "", error: str = ""):
    # --------------------------------------------------------
    # Step 2 of OAuth — Google redirects the user back here
    # after they log in. We exchange the code for credentials.
    # --------------------------------------------------------
    try:
        # Recover the frontend URL saved before redirecting to Google.
        
        if state not in user_credentials or "flow" not in user_credentials[state]:
            raise Exception("Missing OAuth state. Please restart the login flow.")

        print(f"[CALLBACK] Found flow in memory, exchanging code for token...")
        flow_state = user_credentials.pop(state)
        if time.monotonic() - flow_state["created_at"] > 600 or error or not code:
            raise ValueError("Google login expired or was cancelled. Please reconnect.")
        flow = flow_state["flow"]
        client_origin = flow_state.get("client_origin", FRONTEND_URL)
        print(f"[CALLBACK] Client origin: {client_origin}")
        flow.fetch_token(code=code)
        print(f"[CALLBACK] OK Token exchange successful!")

        creds = flow.credentials

        session_id = str(uuid.uuid4())

        user_credentials[session_id] = json.loads(creds.to_json())

        # Save to disk so it survives backend restart
        save_session(session_id, user_credentials[session_id])

        # Clean up the temporary flow state entry
        user_credentials.pop(state, None)
        print(f"[CALLBACK] OK Credentials stored in memory and on disk")

        # Redirect back to the frontend with the session ID
        return RedirectResponse(
            url=f"{client_origin}/confirm?session_id={session_id}&auth=success"
        )

    except Exception as e:
        print(f"[CALLBACK] ERROR ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        return RedirectResponse(
            url=f"{FRONTEND_URL}/confirm?auth=error&message=Google%20login%20failed.%20Please%20reconnect."
        )


@app.post("/confirm")
def confirm_events(request: ConfirmRequest):
    # --------------------------------------------------------
    # Creates all events in the user's Google Calendar.
    # Uses the session_id to find their credentials.
    # --------------------------------------------------------
    try:
        print(f"[CONFIRM] Event count: {len(request.events)}")
        
        # Validate that there are events to create
        if len(request.events) == 0:
            raise HTTPException(
                status_code=400,
                detail="No events to add! Please upload screenshots first."
            )
        
        for event in request.events:
            if event.days and not event.date:
                try:
                    start = date.fromisoformat(event.semester_start or "")
                    end = date.fromisoformat(event.semester_end or "")
                    if end < start:
                        raise ValueError()
                except ValueError:
                    raise HTTPException(status_code=400, detail="Set valid semester start and end dates for every recurring event.")

        # Try to find credentials in memory first
        creds_data = user_credentials.get(request.session_id)
        
        # If not in memory, try to load from disk (in case backend restarted)
        if not creds_data:
            print(f"[CONFIRM] Session not in memory, trying to load from disk...")
            creds_data = load_session(request.session_id)
        
        if not creds_data:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated. Please connect Google Calendar first."
            )

        print(f"[CONFIRM] OK Session found, reconstructing credentials...")
        creds = Credentials.from_authorized_user_info(creds_data, scopes=SCOPES)

        from src.calendar_builder import create_calendar_events_with_creds
        print(f"[CONFIRM] Calling create_calendar_events_with_creds...")
        create_calendar_events_with_creds(
            [event.model_dump() for event in request.events],
            creds
        )

        print(f"[CONFIRM] OK Events created successfully!")
        return JSONResponse(content={"status": "success"})

    except HTTPException:
        raise
    except Exception as e:
        error_msg = "Unable to create calendar events. Please reconnect Google Calendar and try again."
        print(f"[CONFIRM] ERROR ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": error_msg}
        )
