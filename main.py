# ============================================================
# main.py
# ============================================================
# This is the entry point of the entire program.
# "Entry point" means this is the file you actually RUN.
# It's like the director of a movie — it doesn't do the
# work itself, it tells all the other files what to do and
# in what order.
#
# The flow is:
# 1. You give it a screenshot path
# 2. reader.py extracts the text from the screenshot
# 3. parser.py understands the text and finds all events
# 4. We show you everything and ask if it looks correct
# 5. calendar_builder.py creates the events in Google Calendar
# ============================================================


# --- IMPORTS ---

import sys
# "sys" gives us access to system level stuff.
# We use it to read arguments from the command line.
# For example when you type "python main.py schedule.png"
# sys.argv lets us grab that "schedule.png" part.

import os
# Same as before — lets us check if files exist.

from rich.console import Console
# Same as before — for nice colored terminal output.

from src.reader import extract_text_from_screenshot
# Import the function we wrote in reader.py.
# "from src.reader" means "go into the src folder, open reader.py"
# "import extract_text_from_screenshot" means grab that specific function.

from src.parser import parse_schedule, confirm_events
# Import two functions from parser.py.
# parse_schedule — turns raw text into a list of events
# confirm_events — shows the table and asks if it looks correct

from src.calendar_builder import create_calendar_events
# Import the function that creates Google Calendar events.


# --- SETUP ---

console = Console()
# Create our rich console for pretty output.


# --- MAIN FUNCTION ---

def main():
    # --------------------------------------------------------
    # This is the main function that runs the whole program.
    # Everything happens in here in order, step by step.
    # --------------------------------------------------------

    # --- WELCOME MESSAGE ---
    console.print("\n[bold cyan]================================[/bold cyan]")
    console.print("[bold cyan]        SNAPSHOT 📸             [/bold cyan]")
    console.print("[bold cyan]  College Schedule → Calendar   [/bold cyan]")
    console.print("[bold cyan]================================[/bold cyan]\n")
    # Print a nice welcome banner when the program starts.


    # --- STEP 1: GET THE SCREENSHOT PATH ---

    if len(sys.argv) < 2:
        console.print("[bold red]Error: Please provide at least one screenshot path![/bold red]")
        console.print("Usage: [bold]python main.py screenshot1.png screenshot2.png[/bold]\n")
        console.print("Example: [bold]python main.py samples/schedule.png samples/syllabus.png[/bold]\n")
        sys.exit(1)

    # Grab ALL the screenshot paths the user typed
    # sys.argv[1:] means "everything after main.py"
    # so "python main.py a.png b.png" gives us ["a.png", "b.png"]
    image_paths = sys.argv[1:]

    # Check every file exists before we start
    for image_path in image_paths:
        if not os.path.exists(image_path):
            console.print(f"[bold red]Error: Could not find file '{image_path}'[/bold red]")
            console.print("Make sure the path is correct and the file exists.\n")
            sys.exit(1)


    # --- STEP 2: READ THE SCREENSHOT ---

    # Loop through every screenshot and extract text from each one
    # then combine it all into one big string
    all_raw_text = ""

    for image_path in image_paths:
        console.print(f"[bold]Reading screenshot:[/bold] {image_path}\n")

        try:
            raw_text = extract_text_from_screenshot(image_path)
            all_raw_text += raw_text + "\n\n"
            # We add \n\n between each screenshot's text
            # so the parser knows they're separate screenshots
            console.print(f"[bold green]✓ {image_path} read successfully![/bold green]\n")

        except Exception as e:
            console.print(f"[bold red]Error reading {image_path}: {str(e)}[/bold red]")
            console.print("Make sure your OPENAI_API_KEY is set in your .env file.\n")
            sys.exit(1)


    # --- STEP 3: PARSE THE TEXT INTO EVENTS ---

    try:
        events = parse_schedule(all_raw_text)
        # Call parser.py's function to turn the raw text into
        # a clean structured list of events.

        if not events:
            # If the list is empty the AI didn't find any events.
            console.print("[bold red]No events found in the screenshot.[/bold red]")
            console.print("Try a clearer screenshot or a different image.\n")
            sys.exit(1)

        console.print(f"[bold green]✓ Found {len(events)} events![/bold green]\n")
        # len(events) tells us how many events are in the list.

    except Exception as e:
        console.print(f"[bold red]Error parsing schedule: {str(e)}[/bold red]")
        sys.exit(1)


    # --- STEP 4: CONFIRM WITH USER ---

    confirmed_events = confirm_events(events)
    # Show the user a table of everything we found and ask
    # if it looks correct. They can edit anything that's wrong.
    # Returns the (possibly edited) events if they say yes.
    # Returns None if they say no.

    if not confirmed_events:
        # User said no — stop here, don't touch Google Calendar.
        console.print("[yellow]No events were added to Google Calendar.[/yellow]\n")
        sys.exit(0)
        # sys.exit(0) means "stopped successfully" (user chose to stop).


    # --- STEP 5: CREATE GOOGLE CALENDAR EVENTS ---

    try:
        create_calendar_events(confirmed_events)
        # Call calendar_builder.py's function to create all the
        # events in Google Calendar. This is the final step!

    except Exception as e:
        console.print(f"[bold red]Error creating calendar events: {str(e)}[/bold red]")
        console.print("Make sure credentials.json is in your project folder.\n")
        sys.exit(1)


    # --- DONE ---

    console.print("\n[bold cyan]================================[/bold cyan]")
    console.print("[bold cyan]       All done! Good luck 🎓   [/bold cyan]")
    console.print("[bold cyan]================================[/bold cyan]\n")


# --- RUN ---

if __name__ == "__main__":
    # This is a Python convention that means:
    # "only run main() if this file is being run directly"
    # If someone imports main.py into another file this won't run.
    # It's good practice to always have this at the bottom.
    main()
