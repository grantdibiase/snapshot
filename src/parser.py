# ============================================================
# parser.py
# ============================================================
# This file takes the raw text that reader.py extracted from
# the screenshot and makes sense of it.
#
# For example reader.py might give us this messy text:
# "CS 101 MWF 9:00am-10:00am Room 204 Prof. Smith"
#
# parser.py turns that into clean structured data like:
# {
#   "class_name": "CS 101",
#   "days": ["Monday", "Wednesday", "Friday"],
#   "start_time": "9:00 AM",
#   "end_time": "10:00 AM",
#   "location": "Room 204",
#   "professor": "Prof. Smith"
# }
#
# We use OpenAI again here because extracting structured data
# from messy unformatted text is exactly what AI is great at.
# ============================================================


# --- IMPORTS ---

import os
# Same as before — lets us access environment variables
# like our secret API key stored in the .env file.

import json
# "json" is a way of storing structured data as text.
# It looks like a Python dictionary with keys and values.
# Example: {"name": "CS101", "time": "9am"}
# We use it because OpenAI will send us back structured
# data as a JSON string and we need to convert it to
# something Python can actually work with.

from dotenv import load_dotenv
# Same as before — loads our .env file so we can
# access our secret OpenAI API key safely.

from openai import OpenAI
# Same as before — our connection to OpenAI's AI.

from rich.console import Console
from rich.table import Table
# "rich" is a library that makes terminal output look nice.
# Instead of plain boring text, we can print colored tables.
# Console is the main rich object we print through.
# Table lets us build a nice formatted table in the terminal.


# --- SETUP ---

load_dotenv()
# Load the .env file. Same as reader.py.

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Create our OpenAI connection. Same as reader.py.

console = Console()
# Create a "console" object from rich.
# Instead of using Python's built in print() we'll use
# console.print() which gives us colors and formatting.


# --- FUNCTIONS ---

def parse_schedule(raw_text):
    # --------------------------------------------------------
    # This is the MAIN function of this file.
    # It takes the raw messy text from reader.py and sends
    # it to OpenAI with instructions to pull out all the
    # important information in a clean structured format.
    #
    # "raw_text" is just a big string of text — whatever
    # reader.py pulled out of the screenshot.
    # --------------------------------------------------------

    console.print("\n[bold blue]Analyzing your schedule...[/bold blue]")
    # This prints a colored message to the terminal.
    # The [bold blue] tags are rich's way of adding color.
    # \n at the start just adds a blank line before the message.

    response = client.chat.completions.create(
        # Same as reader.py — we're sending a message to OpenAI.

        model="gpt-4o",
        # Same model as before.

        messages=[
            {
                "role": "system",
                "content": """You are a helpful assistant that extracts college schedule information.
                You will be given raw text from a screenshot of a college schedule or syllabus.
                You must extract every single class, event, assignment, or deadline you find.
                
                Always respond with ONLY a JSON array and nothing else.
                No explanation, no extra text, just the raw JSON.
                
                Each item in the array should have these fields:
                - "title": the name of the class or event (string)
                - "days": which days it repeats, e.g. ["Monday", "Wednesday"] or [] if one time only
                - "date": specific date if its a one time event e.g. "2024-09-15" or null if recurring
                - "start_time": start time in 12 hour format e.g. "9:00 AM" or null if unknown  
                - "end_time": end time in 12 hour format e.g. "10:00 AM" or null if unknown
                - "location": room or building or null if unknown
                - "professor": professor name or null if unknown
                - "type": one of "class", "exam", "assignment", "office_hours", "other"
                """
                # This is a "system" message — it sets the rules for how
                # the AI should behave for this entire conversation.
                # We're telling it exactly what format to respond in.
                # The clearer and stricter we are here, the more reliable
                # the output will be. We specifically say "ONLY a JSON array"
                # so it doesn't add any extra words we'd have to clean up.
            },
            {
                "role": "user",
                "content": f"Here is the raw text from the schedule screenshot:\n\n{raw_text}"
                # This is our actual message — the raw text from reader.py.
                # f"..." lets us embed the raw_text variable right in the string.
                # \n\n adds two blank lines between our intro and the actual text.
            }
        ],

        max_tokens=2000
        # Same as before — limits how long the response can be.
    )

    raw_json = response.choices[0].message.content
    # Print what OpenAI sent back so we can see what's happening
    console.print(f"\n[dim]Raw response: {raw_json}[/dim]\n")

    # Sometimes OpenAI wraps JSON in ```json ``` code blocks
    # This strips those out if present
    raw_json = raw_json.strip()
    if raw_json.startswith("```"):
        raw_json = raw_json.split("```")[1]
        if raw_json.startswith("json"):
            raw_json = raw_json[4:]

    events = json.loads(raw_json.strip())

    return events
    # Send the list of events back to whoever called this function.


def display_events(events):
    # --------------------------------------------------------
    # This function takes the list of events that parse_schedule()
    # returned and displays them in a nice table in the terminal.
    #
    # This is the "repeat back to the user" step — before we
    # touch Google Calendar, we show the user exactly what
    # the AI found and ask if it looks correct.
    # --------------------------------------------------------

    console.print("\n[bold green]Here is what I found in your screenshot:[/bold green]\n")
    # Print a colored header message. \n adds blank lines.

    table = Table(show_header=True, header_style="bold magenta")
    # Create a new rich Table object.
    # show_header=True means show column names at the top.
    # header_style makes the column names bold and magenta colored.

    # Add columns to our table — these are the headers
    table.add_column("Title", style="cyan", width=25)
    table.add_column("Type", style="yellow", width=12)
    table.add_column("Days", width=20)
    table.add_column("Date", width=12)
    table.add_column("Time", width=20)
    table.add_column("Location", width=15)
    # Each column has a name and optional width and color.
    # "style" sets the color of the text in that column.

    for event in events:
        # Loop through every event in our list.
        # Each "event" is a dictionary with keys like "title", "days" etc.

        days = ", ".join(event.get("days", []))
        # event.get("days", []) safely gets the days list.
        # If "days" doesn't exist it returns [] instead of crashing.
        # ", ".join() converts ["Monday", "Wednesday"] to "Monday, Wednesday"
        # because tables need strings not lists.

        time = ""
        if event.get("start_time") and event.get("end_time"):
            time = f"{event['start_time']} - {event['end_time']}"
        elif event.get("start_time"):
            time = event["start_time"]
        # Build the time string. If we have both start and end time
        # show "9:00 AM - 10:00 AM". If only start time show just that.
        # If neither exist time stays as empty string "".

        table.add_row(
            event.get("title", "Unknown"),
            event.get("type", "other"),
            days,
            event.get("date") or "",
            time,
            event.get("location") or ""
            # Add one row to the table for this event.
            # event.get("field", "default") safely gets the value
            # and returns a default if it doesn't exist.
            # "or ''" converts None to empty string so table looks clean.
        )

    console.print(table)
    # Actually print the table to the terminal.


def confirm_events(events):
    # --------------------------------------------------------
    # This function shows the events to the user and asks
    # if everything looks correct before touching Google Calendar.
    #
    # This is super important — AI isn't perfect and might
    # misread something. We always want the user to confirm
    # before we actually create calendar events.
    # --------------------------------------------------------

    display_events(events)
    # First show the table of everything we found.

    console.print("\n[bold yellow]Does this look correct?[/bold yellow]")
    console.print("Type [bold green]yes[/bold green] to continue to Google Calendar")
    console.print("Type [bold red]no[/bold red] to edit the events first")
    console.print("Type the [bold]number[/bold] of an event to edit it (e.g. 1, 2, 3)\n")
    # Print instructions for the user in nice colors.

    while True:
        # "while True" means keep looping forever until we
        # hit a "break" or "return" statement below.
        # This lets us keep asking until we get a valid answer.

        user_input = input("Your choice: ").strip().lower()
        # input() pauses the program and waits for the user to type.
        # .strip() removes any accidental spaces before/after.
        # .lower() converts to lowercase so "Yes" and "YES" both work.

        if user_input == "yes":
            console.print("\n[bold green]Great! Building your Google Calendar events...[/bold green]\n")
            return events
            # If they said yes, return the events list as is.
            # The program will move on to calendar_builder.py next.

        elif user_input == "no":
            console.print("\n[bold red]No problem! Please edit the events and run again.[/bold red]\n")
            return None
            # If they said no, return None (nothing).
            # The program will stop before touching Google Calendar.

        elif user_input.isdigit():
            index = int(user_input) - 1
            # Convert their number to a list index.
            # They type "1" for the first event but lists start at 0
            # so we subtract 1.

            if 0 <= index < len(events):
                # Make sure the number they typed is actually valid.
                # len(events) is how many events we have.

                event = events[index]
                # Grab that specific event from the list.

                console.print(f"\n[bold]Editing:[/bold] {event.get('title', 'Unknown')}")
                new_title = input(f"New title (press Enter to keep '{event.get('title')}'): ").strip()
                # Ask them for a new title. If they just hit Enter
                # the input will be "" (empty string) and we keep the old one.

                if new_title:
                    events[index]["title"] = new_title
                    # Only update if they actually typed something.

                console.print("[bold green]Updated![/bold green] Here is the updated schedule:\n")
                display_events(events)
                # Show the updated table so they can see the change.

            else:
                console.print("[bold red]Invalid number, try again.[/bold red]")
                # They typed a number that doesn't match any event.

        else:
            console.print("[bold red]Please type yes, no, or a number.[/bold red]")
            # They typed something completely unexpected.