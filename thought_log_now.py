#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Thought Log Start
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 📓

# Documentation:
# @raycast.description Opens thought log text file in VS Code with timestamp for immediate entry.
# @raycast.author masonc789
# @raycast.authorURL https://raycast.com/masonc789

import subprocess
from datetime import datetime
import os

# Constants
LOG_FILE_PATH = "/Users/colin/Dropbox (Maestral)/Daily Notes/thought log.txt"

# Get the current date and time
current_date = datetime.now().strftime("%-m-%d-%y")
current_time = datetime.now().strftime("%-I:%M %p")
header = f"{current_date}\n---\n"
timestamp = f"{current_time} - \n\n\n"

# Read the existing log file
if os.path.exists(LOG_FILE_PATH):
    with open(LOG_FILE_PATH, "r") as file:
        content = file.read()
else:
    content = ""

import re

# Flag to track if we should add a new timestamp
should_add_timestamp = True

# Use regex to find today's date header (more flexible for whitespace)
# Pattern matches: date, newline, dashes (with optional trailing spaces), newline
date_header_pattern = re.compile(
    r'^' + re.escape(current_date) + r'\n---\s*\n',
    re.MULTILINE
)

# Check if today's date is already in the log file
header_match = date_header_pattern.search(content)

if header_match:
    # Today's date already exists - insert timestamp right after the header
    header_end = header_match.end()
    remaining_content = content[header_end:]

    # Check if there's already an empty timestamp (ends with "- " or "-  " with only whitespace after)
    empty_timestamp_pattern = r'(\d{1,2}:\d{2} [AP]M\s*-\s*)\s*$'

    # Get just the first line after the header (most recent timestamp)
    first_line = remaining_content.split('\n')[0] if remaining_content else ""

    if re.match(empty_timestamp_pattern, first_line.strip()):  # Check if first timestamp is empty
        # Delete the empty timestamp line and its 3 newlines, then add new timestamp
        lines = remaining_content.split('\n', 3)  # Split into: [empty_timestamp, '', '', rest...]
        if len(lines) >= 4:
            # Rejoin from index 3 onward (skipping timestamp + 2 blank lines, keeping the rest)
            remaining_content = '\n'.join(lines[3:])
        else:
            # If less than 4 parts, just clear remaining content (edge case)
            remaining_content = ''

        # Insert the new timestamp right after the header
        content = content[:header_end] + timestamp + remaining_content
        print("Replaced empty timestamp with new one")
    else:
        # Insert the new timestamp right after the header
        content = content[:header_end] + timestamp + remaining_content
else:
    # Today's date doesn't exist - prepend new date header and timestamp
    content = header + timestamp + content

# Only write and trigger KM if we're actually adding a timestamp
if should_add_timestamp:
    # Write the updated content back to the log file
    with open(LOG_FILE_PATH, "w") as file:
        file.write(content)

    ###################
    ## AS OF RIGHT HERE, THE TIMESTAMP IS READY TO GO (E.G. "4:55 PM -")
    ###################

    # run shell command 'keyboardmaestro "Thought log entry"'
    subprocess.run(
        [
            "/usr/bin/osascript",
            "-e",
            'tell application "Keyboard Maestro Engine" to do script "Thought log entry"',
        ]
    )
else:
    # Still focus VS Code to show the empty timestamp, but don't add new one or trigger KM
    print("Empty timestamp detected - focusing VS Code without adding new timestamp")
    # Focus VS Code to bring attention to the empty timestamp
    subprocess.run(["open", "-a", "Visual Studio Code", LOG_FILE_PATH])
