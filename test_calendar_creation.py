#!/usr/bin/env python3
"""
Direct test of calendar event creation using stored credentials.
This bypasses the web flow to isolate the issue.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from google.oauth2.credentials import Credentials
from src.calendar_builder import create_calendar_events_with_creds

# Load the stored Google credentials from token.json
with open("token.json", "r") as f:
    token_data = json.load(f)

# Reconstruct a Credentials object from the stored token
creds = Credentials(
    token=token_data.get("token"),
    refresh_token=token_data.get("refresh_token"),
    token_uri=token_data.get("token_uri"),
    client_id=token_data.get("client_id"),
    client_secret=token_data.get("client_secret"),
    scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/calendar"]),
)

# Test events
test_events = [
    {
        "title": "Test Event 1",
        "date": "2026-03-10",
        "start_time": "10:00 AM",
        "end_time": "11:00 AM",
    },
    {
        "title": "Test Event 2",
        "date": "2026-03-15",
        "start_time": "2:00 PM",
        "end_time": "3:00 PM",
    },
]

print("=" * 60)
print("Testing calendar event creation...")
print("=" * 60)

try:
    create_calendar_events_with_creds(test_events, creds)
    print("\n✅ SUCCESS: Events created in Google Calendar!")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nFull traceback:")
    import traceback
    traceback.print_exc()

print("=" * 60)
