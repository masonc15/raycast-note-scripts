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

# Check if today's date is already in the log file
if header in content:
    # Find the index of today's date and insert the timestamp with two blank lines
    content = content.replace(header, header + timestamp, 1)
else:
    # Prepend the new date and timestamp with two blank lines to the log file
    content = header + timestamp + content

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

# Open the thought log file in VS Code
# subprocess.run(["open", "-a", "Visual Studio Code", LOG_FILE_PATH])
