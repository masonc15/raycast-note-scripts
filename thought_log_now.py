#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Thought Log Start
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 📓

# Documentation:
# @raycast.description Opens thought log in Zed at a fresh timestamp for immediate entry.
# @raycast.author Colin Mason

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Constants
LOG_FILE_PATH = Path(
    os.environ.get(
        "THOUGHT_LOG_PATH",
        "/Users/colin/Dropbox (Maestral)/Daily Notes/thought log.txt",
    )
).expanduser()
NOTES_PATH = Path(
    os.environ.get("DAILY_NOTES_PATH", str(LOG_FILE_PATH.parent))
).expanduser()
ZED_CANDIDATES = (
    "/opt/homebrew/bin/zed",
    "/Applications/Zed.app/Contents/MacOS/cli",
    "/usr/local/bin/zed",
)
NOTES_TZ = ZoneInfo("America/New_York")


def find_zed_binary():
    """Find Zed without depending on the sparse PATH used by GUI launchers."""
    configured = os.environ.get("ZED_CLI")
    if configured:
        return configured

    from_path = shutil.which("zed")
    if from_path:
        return from_path

    for candidate in ZED_CANDIDATES:
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError("Could not find the Zed CLI")

# Get the current date and time
now = datetime.now(NOTES_TZ)
current_date = now.strftime("%-m-%d-%y")
current_time = now.strftime("%-I:%M %p")
header = f"{current_date}\n---\n"
timestamp = f"{current_time} - \n\n\n"

# Read the existing log file
if LOG_FILE_PATH.exists():
    with LOG_FILE_PATH.open("r") as file:
        content = file.read()
else:
    content = ""

# Use regex to find today's date header (more flexible for whitespace)
# Pattern matches: date, newline, dashes (with optional trailing spaces), newline
date_header_pattern = re.compile(
    r'^' + re.escape(current_date) + r'\n---\s*\n',
    re.MULTILINE
)


def clean_empty_timestamps_from_section(section_content):
    """Remove all empty timestamps from a single day's section."""
    empty_ts_pattern = r'(\d{1,2}:\d{2} [AP]M\s*-\s*)\s*$'

    lines = section_content.split('\n')
    result_lines = []
    count_removed = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        if re.match(empty_ts_pattern, line.strip()):
            count_removed += 1
            i += 1
            # Skip trailing blank lines (up to 3)
            blanks_skipped = 0
            while i < len(lines) and lines[i].strip() == '' and blanks_skipped < 3:
                i += 1
                blanks_skipped += 1
        else:
            result_lines.append(line)
            i += 1

    return '\n'.join(result_lines), count_removed


def clean_previous_day_empty_timestamps(file_content):
    """Find first day section and remove its empty timestamps."""
    any_date_pattern = re.compile(r'^(\d{1,2}-\d{2}-\d{2})\n---\s*\n', re.MULTILINE)

    match = any_date_pattern.search(file_content)
    if not match:
        return file_content, 0, None

    previous_date = match.group(1)
    section_start = match.end()

    next_day_match = any_date_pattern.search(file_content, section_start)
    section_end = next_day_match.start() if next_day_match else len(file_content)

    section_content = file_content[section_start:section_end]
    cleaned_section, count_removed = clean_empty_timestamps_from_section(section_content)

    if count_removed > 0:
        file_content = file_content[:section_start] + cleaned_section + file_content[section_end:]

    return file_content, count_removed, previous_date


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
        # Delete ALL consecutive empty timestamps at the top
        lines = remaining_content.split('\n')
        lines_to_skip = 0

        # Count how many empty timestamp blocks to remove (each is 3 lines: timestamp + 2 blank lines)
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(empty_timestamp_pattern, line):
                # This is an empty timestamp, skip it and the next 2 blank lines
                lines_to_skip += 3
                i += 3
            else:
                # Found a non-empty line, stop
                break

        # Rejoin from the point where non-empty content begins
        remaining_content = '\n'.join(lines[lines_to_skip:]) if lines_to_skip < len(lines) else ''

        # Strip any leading newlines since timestamp already includes proper spacing
        remaining_content = remaining_content.lstrip('\n')

        # Insert the new timestamp right after the header
        content = content[:header_end] + timestamp + remaining_content

        num_removed = lines_to_skip // 3
        if num_removed == 1:
            print("Replaced empty timestamp with new one")
        else:
            print(f"Replaced {num_removed} empty timestamps with new one")
    else:
        # Insert the new timestamp right after the header
        content = content[:header_end] + timestamp + remaining_content
else:
    # Today's date doesn't exist - prepend new date header and timestamp
    # First, clean up any empty timestamps from the previous day
    content, removed_count, prev_date = clean_previous_day_empty_timestamps(content)
    if removed_count > 0:
        if removed_count == 1:
            print(f"Cleaned 1 empty timestamp from {prev_date}")
        else:
            print(f"Cleaned {removed_count} empty timestamps from {prev_date}")

    content = header + timestamp + content

# Write the updated content back to the log file
with LOG_FILE_PATH.open("w") as file:
    file.write(content)

# The new timestamp is always the first line after today's header. Passing the
# directory first keeps the file attached to a real Zed worktree, and passing
# the position focuses the already-restored right-hand thought-log pane.
updated_header = date_header_pattern.search(content)
if updated_header is None:
    print("Could not locate the new thought-log timestamp", file=sys.stderr)
    raise SystemExit(1)

timestamp_line = content.count("\n", 0, updated_header.end()) + 1

try:
    subprocess.run(
        [
            find_zed_binary(),
            str(NOTES_PATH),
            f"{LOG_FILE_PATH}:{timestamp_line}",
        ],
        check=True,
    )
except (FileNotFoundError, subprocess.CalledProcessError) as error:
    print(f"Could not open thought log in Zed: {error}", file=sys.stderr)
    raise SystemExit(1) from error
