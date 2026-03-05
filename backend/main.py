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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# We store the user's credentials in memory temporarily.
# In a real production app you'd store these in a database.
# For now this works fine for local and small scale use.
user_credentials = {}


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
async def google_auth():
    # --------------------------------------------------------
    # Step 1 of OAuth — generate the Google login URL and
    # send it back to the frontend so it can redirect the user.
    # --------------------------------------------------------
    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/callback"
        # After login Google sends the user back to this URL
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        # "offline" means we get a refresh token so we don't
        # need the user to log in again every time
        include_granted_scopes="true"
    )

    # Save the state so we can verify it in the callback
    # This prevents CSRF attacks
    user_credentials[state] = {"flow_state": state}

    return JSONResponse(content={"auth_url": auth_url, "state": state})


@app.get("/auth/callback")
async def google_callback(code: str, state: str):
    # --------------------------------------------------------
    # Step 2 of OAuth — Google redirects the user back here
    # after they log in. We exchange the code for credentials.
    # --------------------------------------------------------
    try:
        flow = Flow.from_client_secrets_file(
            "credentials.json",
            scopes=SCOPES,
            redirect_uri="http://localhost:8000/auth/callback",
            state=state
        )

        flow.fetch_token(code=code)
        # Exchange the authorization code for actual credentials

        creds = flow.credentials
        # Now we have real credentials we can use

        session_id = str(uuid.uuid4())
        # Generate a unique ID for this user's session

        user_credentials[session_id] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else [],
        }
        # Save the credentials using the session ID as the key

        # Redirect back to the frontend with the session ID
        # The frontend saves this and sends it with the confirm request
        return RedirectResponse(
            url=f"http://localhost:3000/confirm?session_id={session_id}&auth=success"
        )

    except Exception as e:
        return RedirectResponse(
            url=f"http://localhost:3000/confirm?auth=error&message={str(e)}"
        )


@app.post("/confirm")
async def confirm_events(request: ConfirmRequest):
    # --------------------------------------------------------
    # Creates all events in the user's Google Calendar.
    # Uses the session_id to find their credentials.
    # --------------------------------------------------------
    try:
        if request.session_id not in user_credentials:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated. Please connect Google Calendar first."
            )

        creds_data = user_credentials[request.session_id]
        # Get the saved credentials for this user

        creds = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data["refresh_token"],
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"],
        )
        # Rebuild the credentials object from saved data

        from src.calendar_builder import create_calendar_events_with_creds
        create_calendar_events_with_creds(
            [event.dict() for event in request.events],
            creds
        )

        return JSONResponse(content={"status": "success"})

    except Exception as e:
        print(f"AUTH ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url=f"http://localhost:3000/confirm?auth=error&message={str(e)}"
        )