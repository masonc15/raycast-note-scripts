#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title done task
# @raycast.mode silent

# Optional parameters:
# @raycast.icon ✅
# @raycast.argument1 { "type": "text", "placeholder": "task", "optional": true }

# Documentation:
# @raycast.description Adds completed task along with timestamp to daily note .txt file
# @raycast.author masonc789
# @raycast.authorURL https://raycast.com/masonc789

import sys
from datetime import datetime
import os
import subprocess


def get_daily_note_path():
    """
    Returns the path to the daily note file based on the current date.

    Returns:
        str: The path to the daily note file.

    """
    daily_note_directory = "/Users/colin/Dropbox (Maestral)/Daily Notes"
    current_date = datetime.now().strftime("%m-%d-%y")
    daily_note_filename = f"{current_date}.txt"
    return os.path.join(daily_note_directory, daily_note_filename)


def append_completed_task_to_daily_note(task_name: str, note_path: str):
    """
    Appends the name of a completed task and its timestamp to a daily note file.

    Args:
        task_name (str): The name of the completed task.
        note_path (str): The path to the daily note file.

    Raises:
        FileNotFoundError: If the daily note file does not exist.

    """
    timestamp = datetime.now().strftime("%m-%d-%y %-I:%M %p")
    with open(note_path, "a") as file:
        file.write(f"{task_name} - {timestamp}\n")


def get_topmost_task_from_now(note_path: str):
    """
    Retrieves the topmost task from the 'now' section of the daily note file.

    Args:
        note_path (str): The path to the daily note file.

    Returns:
        tuple: A tuple containing the task name and its line index.

    Raises:
        ValueError: If the 'now' section or tasks are not found in the daily note file.

    """
    with open(note_path, "r") as file:
        content = file.readlines()
        now_section_index = next(
            (i + 2 for i, line in enumerate(content) if line.strip().lower() == "now"),
            None,
        )
        if now_section_index is None:
            raise ValueError("Could not find 'now' section in daily note.")

        for i in range(now_section_index, len(content)):
            if content[i].strip() == "":  # First empty line after 'now' section
                break
            if content[i].strip():  # Found a non-empty line, which is the topmost task
                return content[i].strip(), i

    raise ValueError("No tasks in 'now' section.")


def remove_task_from_now(note_path: str, task_line_index: int):
    """
    Removes a task from the 'now' section of the daily note file and leaves a newline behind.

    Args:
        note_path (str): The path to the daily note file.
        task_line_index (int): The index of the task line to be removed.

    """
    with open(note_path, "r+") as file:
        content = file.readlines()
        content[task_line_index] = "\n"  # Replace the task line with a newline
        file.seek(0)
        file.writelines(content)
        file.truncate()


def remove_one_thing_task():
    """
    Removes task text from One Thing menubar app.
    """
    command = "open --background 'one-thing:?text='"
    subprocess.run(command, shell=True)


if __name__ == "__main__":
    task_name = " ".join(sys.argv[1:]).strip()
    daily_note_path = get_daily_note_path()

    remove_one_thing_task()

    if not task_name:
        try:
            task_name, task_line_index = get_topmost_task_from_now(daily_note_path)
            remove_task_from_now(daily_note_path, task_line_index)
            append_completed_task_to_daily_note(task_name, daily_note_path)
            print(f"Moved '{task_name}' from 'now' to 'done'.")
        except ValueError as e:
            print(e)
            sys.exit(1)
    else:
        append_completed_task_to_daily_note(task_name, daily_note_path)
        print(f"Task '{task_name}' added to daily note.")
