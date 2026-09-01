#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title done task
# @raycast.mode silent

# Optional parameters:
# @raycast.icon ✅
# @raycast.argument1 { "type": "text", "placeholder": "task", "optional": true }

# Documentation:
# @raycast.description Adds a completed task to the daily note and Todoist
# @raycast.author masonc789
# @raycast.authorURL https://raycast.com/masonc789

import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def get_daily_note_path():
    """
    Returns the path to the daily note file based on the current date.

    Returns:
        str: The path to the daily note file.
    """
    daily_note_directory = "/Users/colin/Seshat Drive/Daily Notes"
    current_date = datetime.now().strftime("%-m-%d-%y")
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
    timestamp = datetime.now().strftime("%-m-%d-%y %-I:%M %p")
    with open(note_path, "a") as file:
        file.write(f"{task_name} - {timestamp}\n")


def get_tasks_from_now(note_path: str):
    """
    Retrieves all tasks from the 'now' section of the daily note file.

    Args:
        note_path (str): The path to the daily note file.

    Returns:
        list: A list of tuples containing task names and their line indices.

    Raises:
        ValueError: If the 'now' section is not found in the daily note file.
    """
    tasks = []
    with open(note_path, "r") as file:
        content = file.readlines()
        now_section_index = next(
            (i + 2 for i, line in enumerate(content) if line.strip().lower() == "now"),
            None,
        )
        if now_section_index is None:
            raise ValueError("Could not find 'now' section in daily note.")

        for i in range(now_section_index, len(content)):
            if content[i].strip().lower() == "later":  # Stop at 'later' section
                break
            if content[i].strip():  # Found a non-empty line, which is a task
                tasks.append((content[i].strip(), i))

    return tasks


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


def set_one_thing_task(task_name: str):
    """
    Sets the task in the One Thing app.

    Args:
        task_name (str): The name of the task to set.
    """
    encoded_task_name = quote(task_name)  # URL-encode the task name
    subprocess.Popen(
        [
            "/usr/bin/open",
            "--background",
            f"one-thing:?text={encoded_task_name}",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )


def remove_one_thing_task():
    """
    Removes task text from One Thing menubar app.
    """
    set_one_thing_task("")


TODOIST_API = "https://api.todoist.com/api/v1"
TD_BINARIES = ("td", "/opt/homebrew/bin/td", "/usr/local/bin/td")
HTTP_TIMEOUT = 10
TODOIST_WORKER_ARGUMENT = "--todoist-worker"
TODOIST_ERROR_LOG = os.path.expanduser(
    "~/Library/Logs/raycast-note-scripts/todoist-worker.log"
)


def find_td():
    """
    Return an absolute path to the `td` CLI, or None if it is not installed.
    """
    for candidate in TD_BINARIES:
        if os.path.isabs(candidate) and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def get_todoist_token():
    """
    Resolve a Todoist API token without embedding one in this public script.

    Prefer the process environment (Raycast inherits launchd env). Fall back to
    `td auth token view`, which reads the OS credential store.
    """
    for key in ("TODOIST_API_TOKEN", "TODOIST_API_KEY"):
        token = os.environ.get(key, "").strip()
        if token:
            return token

    td = find_td()
    if not td:
        raise RuntimeError("no TODOIST_API_TOKEN and td is not on PATH")

    result = subprocess.run(
        [td, "--no-spinner", "auth", "token", "view"],
        capture_output=True,
        text=True,
        timeout=HTTP_TIMEOUT,
    )
    token = (result.stdout or "").strip()
    if result.returncode != 0 or not token:
        detail = (result.stderr or result.stdout or "td auth token view failed").strip()
        raise RuntimeError(detail)
    return token


def todoist_request(method, url, token, payload=None, form=None):
    """
    Send an authenticated request to the Todoist API and return parsed JSON or None.
    """
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(form).encode()
    elif payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT) as response:
            body = response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:200].strip()
        raise RuntimeError(f"HTTP {error.code} {detail}".strip()) from error
    except URLError as error:
        raise RuntimeError(f"network error: {error.reason}") from error

    if not body:
        return None
    return json.loads(body.decode())


def log_completed_via_sync(task_name: str, token: str):
    """
    Create a due-today task and close it in one Sync request.
    """
    temp_id = str(uuid.uuid4())
    add_uuid = str(uuid.uuid4())
    close_uuid = str(uuid.uuid4())
    commands = [
        {
            "type": "item_add",
            "temp_id": temp_id,
            "uuid": add_uuid,
            "args": {
                "content": task_name,
                "due": {"string": "today", "lang": "en"},
            },
        },
        {
            "type": "item_close",
            "uuid": close_uuid,
            "args": {"id": temp_id},
        },
    ]
    result = todoist_request(
        "POST",
        f"{TODOIST_API}/sync",
        token,
        form={"commands": json.dumps(commands)},
    )
    if not isinstance(result, dict):
        raise RuntimeError("empty Sync response")

    status = result.get("sync_status") or {}
    add_status = status.get(add_uuid)
    close_status = status.get(close_uuid)
    if add_status != "ok":
        raise RuntimeError(f"item_add failed: {add_status}")
    if close_status == "ok":
        return

    task_id = (result.get("temp_id_mapping") or {}).get(temp_id)
    if not task_id:
        raise RuntimeError(f"item_close failed: {close_status}")
    close_completed_task(task_id, token)


def close_completed_task(task_id: str, token: str):
    """
    Close an existing Todoist task by id.
    """
    todoist_request("POST", f"{TODOIST_API}/tasks/{task_id}/close", token)


def log_completed_via_rest(task_name: str, token: str):
    """
    Create a due-today task, then close it, using REST.
    """
    created = todoist_request(
        "POST",
        f"{TODOIST_API}/tasks",
        token,
        payload={"content": task_name, "due_string": "today"},
    )
    if not isinstance(created, dict) or not created.get("id"):
        raise RuntimeError("create task returned no id")
    close_completed_task(created["id"], token)


def log_completed_via_td(task_name: str):
    """
    Create a due-today task and complete it with the official `td` CLI.
    """
    td = find_td()
    if not td:
        raise RuntimeError("td is not installed")

    add = subprocess.run(
        [td, "--no-spinner", "task", "add", task_name, "--due", "today", "--json"],
        capture_output=True,
        text=True,
        timeout=HTTP_TIMEOUT,
    )
    if add.returncode != 0:
        detail = (add.stderr or add.stdout or "td task add failed").strip()
        raise RuntimeError(detail)

    try:
        created = json.loads(add.stdout)
        task_id = created.get("id")
    except json.JSONDecodeError as error:
        raise RuntimeError("td task add returned non-JSON") from error
    if not task_id:
        raise RuntimeError("td task add returned no id")

    complete = subprocess.run(
        [td, "--no-spinner", "task", "complete", f"id:{task_id}"],
        capture_output=True,
        text=True,
        timeout=HTTP_TIMEOUT,
    )
    if complete.returncode != 0:
        detail = (complete.stderr or complete.stdout or "td task complete failed").strip()
        raise RuntimeError(detail)


def log_completed_task_to_todoist(task_name: str):
    """
    Record the task as completed today in Todoist.

    Uses the Sync API first (one request: add due today, then close). Falls
    back to REST, then to `td`. Token comes from the environment or `td`.
    """
    errors = []

    try:
        token = get_todoist_token()
    except Exception as error:
        token = None
        errors.append(f"token: {error}")
    else:
        for name, action in (
            ("sync", log_completed_via_sync),
            ("rest", log_completed_via_rest),
        ):
            try:
                action(task_name, token)
                return
            except Exception as error:
                errors.append(f"{name}: {error}")

    try:
        log_completed_via_td(task_name)
        return
    except Exception as error:
        errors.append(f"td: {error}")

    raise RuntimeError("; ".join(errors))


def queue_completed_task_to_todoist(task_name: str):
    """
    Start Todoist logging in a detached process so Raycast can return at once.
    """
    subprocess.Popen(
        [
            sys.executable or "/usr/bin/python3",
            os.path.abspath(__file__),
            TODOIST_WORKER_ARGUMENT,
            task_name,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )


def run_todoist_worker(task_name: str):
    """
    Log one completed task. Record failures because the worker has no HUD.
    """
    try:
        log_completed_task_to_todoist(task_name)
    except Exception as error:
        log_directory = os.path.dirname(TODOIST_ERROR_LOG)
        os.makedirs(log_directory, exist_ok=True)
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with open(TODOIST_ERROR_LOG, "a", encoding="utf-8") as log_file:
            log_file.write(f"{timestamp} {task_name!r}: {error}\n")


def with_todoist_status(message: str, todoist_error):
    """
    Print a silent-mode HUD line that includes the Todoist queue outcome.
    """
    if todoist_error is None:
        print(f"{message} Todoist queued.")
    else:
        print(f"{message} Todoist queue failed: {todoist_error}")


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments[:1] == [TODOIST_WORKER_ARGUMENT]:
        task_name = " ".join(arguments[1:]).strip()
        if task_name:
            run_todoist_worker(task_name)
        return

    task_name = " ".join(arguments).strip()
    daily_note_path = get_daily_note_path()

    if not task_name:
        try:
            tasks = get_tasks_from_now(daily_note_path)
            if not tasks:
                raise ValueError("No tasks in 'now' section.")
            
            task_name, task_line_index = tasks[0]  # Get the topmost task
            remove_task_from_now(daily_note_path, task_line_index)
            append_completed_task_to_daily_note(task_name, daily_note_path)
            todoist_error = None
            try:
                queue_completed_task_to_todoist(task_name)
            except Exception as error:
                todoist_error = error

            # Check if there are more tasks in the 'now' section
            remaining_tasks = get_tasks_from_now(daily_note_path)
            if remaining_tasks:
                next_task = remaining_tasks[0][0]  # Get the name of the next task
                set_one_thing_task(next_task)
            else:
                remove_one_thing_task()
            with_todoist_status(
                f"Moved '{task_name}' from 'now' to 'done'.", todoist_error
            )
        except ValueError as e:
            print(e)
            sys.exit(1)
    else:
        append_completed_task_to_daily_note(task_name, daily_note_path)
        todoist_error = None
        try:
            queue_completed_task_to_todoist(task_name)
        except Exception as error:
            todoist_error = error
        with_todoist_status(
            f"Task '{task_name}' added to daily note.", todoist_error
        )


if __name__ == "__main__":
    main()
