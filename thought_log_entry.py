#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title thought log entry
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 📓
# @raycast.argument1 { "type": "text", "placeholder": "thought log entry" }

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
