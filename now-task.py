#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title now task
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 📝
# @raycast.argument1 { "type": "text", "placeholder": "task", "optional": true }
# @raycast.argument2 { "type": "text", "placeholder": "duration (minutes)", "optional": true }

# Documentation:
# @raycast.description Adds a task to the "now" section of the current day's daily note.
# @raycast.author masonc789
# @raycast.authorURL https://raycast.com/masonc789

import sys
import os
import subprocess
from datetime import datetime
from urllib.parse import quote
from typing import Any


def get_daily_note_path():
    """
    Get the path to the daily note file.

    Returns:
        str: The path to the daily note file.
    """
    daily_note_directory = os.path.expanduser("~/Daily Notes/")
    current_date = datetime.now().strftime("%-m-%d-%y")
    daily_note_filename = f"{current_date}.txt"
    return os.path.join(daily_note_directory, daily_note_filename)


def add_to_now_section(task_name: str, note_path: str):
    """
    Add the task to the 'now' section of the daily note file.

    Args:
        task_name (str): The name of the task to add.
        note_path (str): The path to the daily note file.
    """
    if not os.path.exists(note_path):
        print(f"Daily note for today does not exist at {note_path}")
        sys.exit(1)

    with open(note_path, "r+") as file:
        insert_task_into_now_section(file, task_name)


def insert_task_into_now_section(file: Any, task_name: str) -> None:
    """
    Insert a task into the 'now' section of the daily note file.

    Args:
        file (Any): The file object representing the daily note file.
        task_name (str): The name of the task to insert.
    """
    content = file.readlines()
    now_section_index = next(
        (i + 2 for i, line in enumerate(content) if line.strip().lower() == "now"),
        None,
    )
    if now_section_index is None:
        print("Could not find 'now' section in daily note.")
        sys.exit(1)

    content.insert(now_section_index, f"{task_name}\n")
    file.seek(0)
    file.writelines(content)


def set_one_thing_task(task_name: str):
    """
    Set the task in the One Thing app.

    Args:
        task_name (str): The name of the task to set.
    """
    encoded_task_name = quote(task_name)  # URL-encode the task name
    command = f"open --background 'one-thing:?text={encoded_task_name}'"
    subprocess.run(command, shell=True, check=True)


def get_topmost_now_task(note_path: str) -> str:
    """
    Get the topmost task in the 'now' section of the daily note file.

    Args:
        note_path (str): The path to the daily note file.

    Returns:
        str: The topmost task in the 'now' section.
    """
    try:
        with open(note_path, "r") as file:
            content = file.readlines()
            now_section_index = next(
                (i for i, line in enumerate(content) if line.strip().lower() == "now"),
                None,
            )
            if now_section_index is None:
                raise ValueError("Could not find 'now' section in daily note.")
            for task_line in content[now_section_index + 2 :]:
                if task_line.strip().lower() == "later":  # Stop at 'later' section
                    break
                if task_line.strip():  # Found a non-empty line, which is our task
                    return task_line.strip()
            return ""  # No tasks found in 'now' section
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Daily note for today does not exist at {note_path}"
        ) from e


def is_timerpro_running() -> bool:
    """
    Check if AS TimerPRO.app is already running.

    Returns:
        bool: True if the app is running, False otherwise.
    """
    result = subprocess.run(
        ["pgrep", "-f", "AS TimerPRO.app"], stdout=subprocess.PIPE, text=True
    )
    return result.stdout != ""


def quit_timerpro():
    """
    Quit AS TimerPRO.app if it's running.
    """
    subprocess.run(["pkill", "-f", "AS TimerPRO.app"])


def start_timerpro_timer(duration_minutes: int):
    """
    Start a countdown timer in AS TimerPRO.app for the given duration in minutes.

    Args:
        duration_minutes (int): The duration of the timer in minutes.
    """
    hours, minutes = divmod(duration_minutes, 60)
    timer_command = f"{{Timer#0:H{hours:02d}M{minutes:02d}S00 ModeTimer Start}}"
    subprocess.Popen(
        ["/Applications/AS TimerPRO.app/Contents/MacOS/AS TimerPRO", timer_command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


if __name__ == "__main__":
    task_name = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    task_duration = (
        int(sys.argv[2].strip())
        if len(sys.argv) > 2 and sys.argv[2].strip().isdigit()
        else None
    )
    daily_note_path = get_daily_note_path()

    if task_name:
        add_to_now_section(task_name, daily_note_path)
        print(f"Task '{task_name}' added to 'now' section of daily note.")

        if task_duration is not None:
            if is_timerpro_running():
                quit_timerpro()
            start_timerpro_timer(task_duration)
            print(f"Timer set for {task_duration} minutes.")

    else:
        try:
            task_name = get_topmost_now_task(daily_note_path)
        except (ValueError, FileNotFoundError) as e:
            print(e)
            sys.exit(1)

    set_one_thing_task(task_name)
