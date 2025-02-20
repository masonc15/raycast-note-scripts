#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title later task
# @raycast.mode silent

# Optional parameters:
# @raycast.icon ⌛️
# @raycast.argument1 { "type": "text", "placeholder": "task" }

# Documentation:
# @raycast.description Adds a task to the "later" section of the current day's daily note. Use '-b' at the end to add to the bottom.
# @raycast.author masonc789
# @raycast.authorURL https://raycast.com/masonc789

import sys
import os
from datetime import datetime


def get_daily_note_path():
    """
    Get the path to the daily note file.

    Returns:
        str: The path to the daily note file.
    """
    daily_note_directory = "/Users/colin/Dropbox (Maestral)/Daily Notes"
    current_date = datetime.now().strftime("%-m-%d-%y")
    daily_note_filename = f"{current_date}.txt"
    return os.path.join(daily_note_directory, daily_note_filename)


def find_later_section(content):
    """
    Find the index of the 'later' section heading, confirmed by a following '---' line.

    Args:
        content (list): List of lines in the file.

    Returns:
        int or None: Index of the 'later' heading, or None if not found.
    """
    for i in range(len(content) - 1):
        if content[i].strip().lower() == "later" and content[i + 1].strip() == "---":
            return i
    return None


def find_next_heading(content, start):
    """
    Find the index of the next heading after the given start index.

    Args:
        content (list): List of lines in the file.
        start (int): Starting index to search from.

    Returns:
        int: Index of the next heading, or len(content) if none found.
    """
    for j in range(start + 2, len(content) - 1):
        if content[j].strip() and content[j + 1].strip() == "---":
            return j
    return len(content)


def add_to_later_section(task_name: str, note_path: str, add_to_bottom: bool = False):
    """
    Add the task to the 'later' section of the daily note, either at the top or bottom.

    Args:
        task_name (str): The name of the task to add.
        note_path (str): Path to the daily note file.
        add_to_bottom (bool): If True, add to the bottom; otherwise, add to the top.
    """
    if not os.path.exists(note_path):
        print(f"Daily note for today does not exist at {note_path}")
        sys.exit(1)

    with open(note_path, "r+") as file:
        content = file.readlines()
        later_index = find_later_section(content)
        if later_index is None:
            raise ValueError("Could not find 'later' section in daily note.")

        section_start = later_index + 2  # Position after '---'
        next_heading_index = find_next_heading(content, later_index)

        if not add_to_bottom:
            # Add to top, right after the '---' line
            content.insert(section_start, f"{task_name}\n\n")
        else:
            # Add to bottom, before the next heading or at file end
            content.insert(next_heading_index, f"{task_name}\n\n")

        file.seek(0)
        file.writelines(content)
        file.truncate()


if __name__ == "__main__":
    # Parse the input to check for the '-b' flag
    task_input = sys.argv[1].strip()
    words = task_input.split()
    if words and words[-1] == "-b":
        task_name = " ".join(words[:-1])
        add_to_bottom = True
    else:
        task_name = task_input
        add_to_bottom = False

    # Ensure a task name is provided
    if not task_name:
        print("No task provided. Exiting.")
        sys.exit(1)

    note_path = get_daily_note_path()
    add_to_later_section(task_name, note_path, add_to_bottom)

    print(
        f"Added task '{task_name}' to {'bottom' if add_to_bottom else 'top'} of later section in daily note."
    )
