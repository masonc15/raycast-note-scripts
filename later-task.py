#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title later task
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 🔜
# @raycast.argument1 { "type": "text", "placeholder": "task" }

# Documentation:
# @raycast.description Adds a task to the "later" section of the current day's daily note.
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
    daily_note_directory = os.getenv("DAILY_NOTE_DIRECTORY")
    current_date = datetime.now().strftime("%m-%d-%y")
    daily_note_filename = f"{current_date}.txt"
    return os.path.join(daily_note_directory, daily_note_filename)


def add_to_later_section(task_name: str, note_path: str):
    """
    Add the task to the 'later' section of the daily note file, followed by two newlines.

    Args:
        task_name (str): The name of the task to add.
        note_path (str): The path to the daily note file.
    """
    if not os.path.exists(note_path):
        print(f"Daily note for today does not exist at {note_path}")
        sys.exit(1)

    later_section_found = False
    with open(note_path, "r+") as file:
        content = file.readlines()
        for i, line in enumerate(content):
            if line.strip().lower() == "later":
                later_section_found = True
            elif later_section_found and line.strip().lower() == "done":
                content.insert(i, f"{task_name}\n\n")
                break
        if not later_section_found:
            raise ValueError("Could not find 'later' section in daily note.")

        file.seek(0)
        file.writelines(content)
        file.truncate()


if __name__ == "__main__":
    task_name = " ".join(sys.argv[1:]).strip()
    if not task_name:
        print("No task provided. Exiting.")
        sys.exit(1)

    note_path = get_daily_note_path()
    add_to_later_section(task_name, note_path)

    print(f"Added task '{task_name}' to later section of daily note.")
