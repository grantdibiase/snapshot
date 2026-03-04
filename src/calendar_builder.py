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
# Same as before — lets us access files and environment variables.

import datetime
# "datetime" is Python's built in tool for working with dates and times.
# We need it because Google Calendar expects dates in a very specific format.

from google.oauth2.credentials import Credentials
# This handles storing your Google login credentials (your proof of identity).
# After you log in the first time it saves a token.json file so you
# don't have to log in every single time you run the program.

from google_auth_oauthlib.flow import InstalledAppFlow
# This is what triggers the browser popup for logging in.
# "InstalledAppFlow" means this is a desktop/installed app (not a website).

from google.auth.transport.requests import Request
# This lets us refresh your login token when it expires.
# Tokens expire after a while for security reasons.
# This quietly refreshes it in the background so you never notice.

from googleapiclient.discovery import build
# "build" creates our actual connection to the Google Calendar API.
# Think of it like creating a remote control for your Google Calendar.

from rich.console import Console
# Same as parser.py — for nice colored terminal output.


# --- SETUP ---

console = Console()
# Create our rich console for pretty terminal output.

SCOPES = ["https://www.googleapis.com/auth/calendar"]
# "SCOPES" tells Google exactly what permissions our app needs.
# This one means "read and write access to Google Calendar".
# Google will show this permission to the user during login
# so they know exactly what the app can do.


# --- FUNCTIONS ---

def authenticate_google():
    # --------------------------------------------------------
    # This function handles logging into Google.
    # It checks if you've already logged in before.
    # If yes it reuses your saved login (token.json).
    # If no it opens a browser window for you to log in.
    #
    # After this function runs successfully we have a
    # "credentials" object that proves who we are to Google.
    # --------------------------------------------------------

    creds = None
    # Start with no credentials. We'll find or create them below.

    if os.path.exists("token.json"):
        # Check if we've logged in before.
        # token.json is a file that gets created after your first login.
        # It stores your login info so you don't have to log in every time.

        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # Load the saved credentials from token.json.

    if not creds or not creds.valid:
        # If we don't have credentials OR they've expired, we need to
        # either refresh them or get new ones by logging in again.

        if creds and creds.expired and creds.refresh_token:
            # If credentials exist but are just expired, quietly refresh them.
            # This is like renewing a library card — same person, new card.
            creds.refresh(Request())

        else:
            # No saved credentials at all — need to log in fresh.
            # This opens a browser window for you to log into Google.

            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            # Load our app's identity from credentials.json.
            # This is the file we downloaded from Google Cloud Console earlier.
            # It tells Google "this request is coming from the snapshot app".

            creds = flow.run_local_server(port=0)
            # Open the browser login window.
            # port=0 means use any available port automatically.
            # This will pause the program until you finish logging in.

        with open("token.json", "w") as token:
            token.write(creds.to_json())
            # Save the credentials to token.json so we don't need to
            # log in again next time. to_json() converts it to a string
            # we can save to a file.

    return creds
    # Send the credentials back so we can use them to talk to Google Calendar.


def format_event_for_google(event):
    # --------------------------------------------------------
    # This function takes ONE event from our parsed list and
    # converts it into the exact format Google Calendar expects.
    #
    # Google is very specific about how events need to be formatted.
    # For example dates must be "2024-09-15" and times must be
    # "2024-09-15T09:00:00" — Google won't accept anything else.
    # --------------------------------------------------------

    google_event = {
        "summary": event.get("title", "Untitled Event"),
        # "summary" is what Google calls the event title.
        # It's what shows up on your calendar as the event name.
    }

    if event.get("location"):
        google_event["location"] = event["location"]
        # Only add location if we actually have one.
        # Google Calendar shows this under the event details.

    if event.get("type") == "exam":
        google_event["colorId"] = "11"
        # Color exams red so they stand out on your calendar.
        # Google Calendar has numbered color IDs (11 = red).
    elif event.get("type") == "assignment":
        google_event["colorId"] = "5"
        # Color assignments yellow/banana.
    elif event.get("type") == "class":
        google_event["colorId"] = "9"
        # Color regular classes blue/blueberry.

    today = datetime.date.today()
    # Get today's date. We need this to figure out actual dates
    # for recurring events like "every Monday at 9am".

    if event.get("date"):
        # This is a one-time event with a specific date like an exam.

        date_str = event["date"]
        # The date string from our parser e.g. "2024-10-15"

        if event.get("start_time"):
            # If we have a specific time, create a timed event.

            start_dt = f"{date_str}T{convert_to_24hr(event['start_time'])}"
            end_dt = f"{date_str}T{convert_to_24hr(event.get('end_time', event['start_time']))}"
            # Google needs datetime in format "2024-10-15T09:00:00"
            # We combine the date and time with a "T" in between.

            google_event["start"] = {"dateTime": start_dt, "timeZone": "America/New_York"}
            google_event["end"] = {"dateTime": end_dt, "timeZone": "America/New_York"}
            # "start" and "end" are required by Google.
            # timeZone tells Google what timezone we're in.
            # We'll make this configurable later.

        else:
            # No specific time — make it an all day event.
            google_event["start"] = {"date": date_str}
            google_event["end"] = {"date": date_str}

    elif event.get("days"):
        # This is a recurring event like a class that happens every week.

        day_map = {
            "monday": "MO", "tuesday": "TU", "wednesday": "WE",
            "thursday": "TH", "friday": "FR", "saturday": "SA", "sunday": "SU"
        }
        # Google uses two letter abbreviations for days in recurring rules.
        # This dictionary maps full day names to Google's abbreviations.

        recurrence_days = ",".join([
            day_map[d.lower()]
            for d in event["days"]
            if d.lower() in day_map
        ])
        # Convert our days list like ["Monday", "Wednesday"] to "MO,WE"
        # which is what Google's recurrence rule format requires.

        if recurrence_days:
            google_event["recurrence"] = [
                f"RRULE:FREQ=WEEKLY;BYDAY={recurrence_days};COUNT=16"
                # This tells Google "repeat this event every week
                # on these days, for 16 weeks (one semester)".
                # RRULE is the standard format for recurring calendar events.
            ]

        if event.get("start_time"):
            start_dt = f"{today}T{convert_to_24hr(event['start_time'])}"
            end_dt = f"{today}T{convert_to_24hr(event.get('end_time', event['start_time']))}"
            google_event["start"] = {"dateTime": start_dt, "timeZone": "America/New_York"}
            google_event["end"] = {"dateTime": end_dt, "timeZone": "America/New_York"}

    else:
        # No date and no days — just make it an all day event for today
        # as a fallback so nothing gets lost.
        google_event["start"] = {"date": str(today)}
        google_event["end"] = {"date": str(today)}

    return google_event
    # Send the formatted event back ready for Google Calendar.


def convert_to_24hr(time_str):
    # --------------------------------------------------------
    # Google Calendar needs times in 24 hour format like "09:00:00"
    # but our parser gives us 12 hour format like "9:00 AM".
    # This function converts between the two.
    # --------------------------------------------------------

    try:
        time_obj = datetime.datetime.strptime(time_str.strip(), "%I:%M %p")
        # strptime means "string parse time" — it reads a time string.
        # "%I:%M %p" is the pattern for 12 hour time like "9:00 AM"
        # %I = hours (12hr), %M = minutes, %p = AM/PM

        return time_obj.strftime("%H:%M:%S")
        # strftime means "string format time" — it formats a time as string.
        # "%H:%M:%S" is 24 hour format like "09:00:00"
        # %H = hours (24hr), %M = minutes, %S = seconds

    except:
        return "09:00:00"
        # If anything goes wrong just default to 9am.
        # Better to create the event at the wrong time than crash.


def create_calendar_events(events):
    # --------------------------------------------------------
    # This is the MAIN function of this file.
    # It takes our full list of events, logs into Google,
    # and creates every single event in Google Calendar.
    # --------------------------------------------------------

    console.print("\n[bold blue]Connecting to Google Calendar...[/bold blue]")

    creds = authenticate_google()
    # Log into Google and get our credentials.

    service = build("calendar", "v3", credentials=creds)
    # Build our Google Calendar "remote control".
    # "calendar" = which Google service we want
    # "v3" = which version of the API
    # credentials = prove who we are

    console.print("[bold green]Connected! Creating your events...[/bold green]\n")

    created = 0
    failed = 0
    # Keep count of how many events we create successfully vs fail.

    for event in events:
        # Loop through every event in our list.

        try:
            google_event = format_event_for_google(event)
            # Convert our event to Google's format.

            result = service.events().insert(
                calendarId="primary",
                body=google_event
            ).execute()
            # Actually create the event in Google Calendar!
            # calendarId="primary" means use the main calendar.
            # body=google_event is the event data we're sending.
            # .execute() sends the request and gets the response.

            created += 1
            console.print(f"[green]✓[/green] Created: {event.get('title', 'Untitled')}")
            # Print a green checkmark for each successful event.

        except Exception as e:
            failed += 1
            console.print(f"[red]✗[/red] Failed: {event.get('title', 'Untitled')} — {str(e)}")
            # Print a red X if something went wrong with this event.
            # We don't crash the whole program — just skip this one and continue.

    console.print(f"\n[bold green]Done! Created {created} events.[/bold green]")
    if failed > 0:
        console.print(f"[bold red]{failed} events failed — check the errors above.[/bold red]")
    # Print a final summary of how many events were created vs failed.