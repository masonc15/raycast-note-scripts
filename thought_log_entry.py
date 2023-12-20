#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title thought log entry
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 📓
# @raycast.argument1 { "type": "text", "placeholder": "journal entry" }

# Documentation:
# @raycast.description Adds a timestamped entry to thought log text file.
# @raycast.author masonc789
# @raycast.authorURL https://raycast.com/masonc789

import sys
from datetime import datetime
import os

# Constants
LOG_FILE_PATH = "/Users/colin/Dropbox (Maestral)/Daily Notes/thought log.txt"

# Get the current date and time
current_date = datetime.now().strftime("%-m-%d-%y")
current_time = datetime.now().strftime("%-I:%M %p")
header = f"{current_date}\n---\n"

# Get the entry from the argument
entry = sys.argv[1].strip()
formatted_entry = f"{current_time} - {entry}\n"

# Read the existing log file
if os.path.exists(LOG_FILE_PATH):
    with open(LOG_FILE_PATH, "r") as file:
        content = file.read()

    # Check if today's date is already in the log file
    if header in content:
        # Find the index of today's date and insert the entry
        content = content.replace(header, header + formatted_entry + "\n\n", 1)
    else:
        # Prepend the new date, entry, and three blank lines to the log file
        content = header + formatted_entry + "\n\n\n" + content

    # Write the updated content back to the log file
    with open(LOG_FILE_PATH, "w") as file:
        file.write(content)
else:
    # Create a new log file with the entry
    with open(LOG_FILE_PATH, "w") as file:
        file.write(header + formatted_entry + "\n\n\n")
