# ============================================================
# calendar_builder.py
# ============================================================
# This is the last step in our pipeline.
# It takes the clean list of events that parser.py built
# and actually creates them inside your Google Calendar.
#
# To talk to Google Calendar we need to:
# 1. Prove we are who we say we are (authentication)
# 2. Send each event in the exact format Google expects
#
# Google uses something called "OAuth" for authentication.
# OAuth is basically Google saying "hey prove this is really
# you" by making you log in through a browser popup the
# first time. After that it remembers you automatically.
# ============================================================


# --- IMPORTS ---

import os
import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from rich.console import Console


# --- SETUP ---

console = Console()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
# Tells Google we need read and write access to Google Calendar.


# --- FUNCTIONS ---

def authenticate_google():
    # --------------------------------------------------------
    # Handles logging into Google.
    # Checks if you've already logged in before via token.json.
    # If yes reuses saved login. If no opens browser to log in.
    # --------------------------------------------------------

    creds = None

    if os.path.exists("token.json"):
        # We've logged in before — load saved credentials
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Credentials exist but expired — quietly refresh them
            creds.refresh(Request())
        else:
            # No saved credentials — open browser login window
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())
            # Save credentials so we don't need to log in next time

    return creds


def format_event_for_google(event):
    # --------------------------------------------------------
    # Takes ONE event from our parsed list and converts it
    # into the exact format Google Calendar expects.
    # --------------------------------------------------------

    google_event = {
        "summary": event.get("title", "Untitled Event"),
    }

    if event.get("location"):
        google_event["location"] = event["location"]

    # Color code events by type so they stand out on your calendar
    if event.get("type") == "exam":
        google_event["colorId"] = "11"    # Red
    elif event.get("type") == "assignment":
        google_event["colorId"] = "5"     # Yellow
    elif event.get("type") == "class":
        google_event["colorId"] = "9"     # Blue

    today = datetime.date.today()

    # Map day names to Google's two letter abbreviations
    day_map = {
        "monday": "MO", "tuesday": "TU", "wednesday": "WE",
        "thursday": "TH", "friday": "FR", "saturday": "SA", "sunday": "SU"
    }

    if event.get("date"):
        # --------------------------------------------------------
        # ONE TIME EVENT — has a specific date like an exam
        # --------------------------------------------------------
        date_str = event["date"]

        if event.get("start_time"):
            start_dt = f"{date_str}T{convert_to_24hr(event['start_time'])}"
            end_dt = f"{date_str}T{convert_to_24hr(event.get('end_time', event['start_time']))}"
            google_event["start"] = {"dateTime": start_dt, "timeZone": "America/New_York"}
            google_event["end"] = {"dateTime": end_dt, "timeZone": "America/New_York"}
        else:
            # No time — make it an all day event
            google_event["start"] = {"date": date_str}
            google_event["end"] = {"date": date_str}

    elif event.get("days"):
        # --------------------------------------------------------
        # RECURRING EVENT — repeats every week like a class
        # --------------------------------------------------------

        recurrence_days = ",".join([
            day_map[d.lower()]
            for d in event["days"]
            if d.lower() in day_map
        ])
        # Converts ["Monday", "Wednesday"] to "MO,WE"

        if recurrence_days:
            # Use semester_end if we have it, otherwise default to 16 weeks
            if event.get("semester_end"):
                # UNTIL tells Google exactly when to stop repeating
                # Must be in this exact format: 20241215T000000Z
                until_date = event["semester_end"].replace("-", "") + "T000000Z"
                google_event["recurrence"] = [
                    f"RRULE:FREQ=WEEKLY;BYDAY={recurrence_days};UNTIL={until_date}"
                ]
            else:
                google_event["recurrence"] = [
                    f"RRULE:FREQ=WEEKLY;BYDAY={recurrence_days};COUNT=16"
                ]

        if event.get("start_time"):
            # Get the semester start date
            if event.get("semester_start"):
                semester_start = datetime.date.fromisoformat(event["semester_start"])
            else:
                semester_start = today

            # Find Monday of the semester start week
            days_since_monday = semester_start.weekday()
            monday_of_week = semester_start - datetime.timedelta(days=days_since_monday)

            # Find the FIRST class day of the week starting from Monday.
            # The first occurrence MUST land on an actual class day.
            # Otherwise Google creates a phantom event on the wrong day.
            # Example: MO/WE class → first occurrence is Monday of that week
            # Example: TU/TH class → first occurrence is Tuesday of that week
            # Example: TH only class → first occurrence is Thursday of that week
            first_occurrence = None
            for offset in range(7):
                # Check each day starting from Monday of the semester week
                candidate = monday_of_week + datetime.timedelta(days=offset)
                candidate_day_name = candidate.strftime("%A").lower()
                # strftime("%A") returns full day name e.g. "Monday", "Tuesday"
                # .lower() converts to lowercase to match our event days list

                if candidate_day_name in [d.lower() for d in event["days"]]:
                    # This candidate day is one of the actual class days!
                    first_occurrence = candidate
                    break
                    # Stop as soon as we find the first class day of the week

            if first_occurrence is None:
                # Fallback just in case nothing matched
                first_occurrence = semester_start

            start_dt = f"{first_occurrence}T{convert_to_24hr(event['start_time'])}"
            end_dt = f"{first_occurrence}T{convert_to_24hr(event.get('end_time', event['start_time']))}"
            google_event["start"] = {"dateTime": start_dt, "timeZone": "America/New_York"}
            google_event["end"] = {"dateTime": end_dt, "timeZone": "America/New_York"}

    else:
        # --------------------------------------------------------
        # NO DATE AND NO DAYS — fallback to all day event today
        # so nothing gets lost
        # --------------------------------------------------------
        google_event["start"] = {"date": str(today)}
        google_event["end"] = {"date": str(today)}

    return google_event


def convert_to_24hr(time_str):
    # --------------------------------------------------------
    # Google Calendar needs times in 24 hour format "09:00:00"
    # but our parser gives us 12 hour format "9:00 AM".
    # This converts between the two.
    # --------------------------------------------------------

    try:
        time_obj = datetime.datetime.strptime(time_str.strip(), "%I:%M %p")
        # strptime reads a time string using the pattern we give it
        # %I = hours (12hr), %M = minutes, %p = AM/PM

        return time_obj.strftime("%H:%M:%S")
        # strftime formats it back as a string
        # %H = hours (24hr), %M = minutes, %S = seconds

    except:
        return "09:00:00"
        # If anything goes wrong default to 9am


def create_calendar_events(events):
    # --------------------------------------------------------
    # MAIN function of this file.
    # Logs into Google and creates every event in Google Calendar.
    # --------------------------------------------------------

    console.print("\n[bold blue]Connecting to Google Calendar...[/bold blue]")

    creds = authenticate_google()
    service = build("calendar", "v3", credentials=creds)

    console.print("[bold green]Connected! Creating your events...[/bold green]\n")

    created = 0
    failed = 0

    for event in events:
        try:
            google_event = format_event_for_google(event)

            result = service.events().insert(
                calendarId="primary",
                body=google_event
            ).execute()
            # Create the event in Google Calendar!
            # calendarId="primary" = use the main calendar

            created += 1
            console.print(f"[green]✓[/green] Created: {event.get('title', 'Untitled')}")

        except Exception as e:
            failed += 1
            console.print(f"[red]✗[/red] Failed: {event.get('title', 'Untitled')} — {str(e)}")

    console.print(f"\n[bold green]Done! Created {created} events.[/bold green]")
    if failed > 0:
        console.print(f"[bold red]{failed} events failed — check the errors above.[/bold red]")