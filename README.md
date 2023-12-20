# raycast-note-scripts

My collection of Raycast script commands for managing and manipulating tasks within my daily note files. Most scripts also integrate with the [One Thing](https://sindresorhus.com/one-thing) menubar app when possible.

## Scripts

### `done-task.py`

Adds completed tasks along with a timestamp to the "done" section of the daily note .txt file. If no task is provided, it moves the topmost task from the "now" section to the "done" section and updates the One Thing menubar app.

### `now-task.py`

Adds a task to the "now" section of the current day's daily note. If no task is provided, it retrieves the topmost task from the "now" section and sets it in the One Thing menubar app.

### `later-task.py`

Adds a task to the "later" section of the current day's daily note. The task is followed by two newlines to separate it from subsequent tasks.

## Usage

Add the scripts to your Raycast script commands directory.

> [!NOTE]
> Make sure to replace the `daily_note_directory` in each script with the path to your daily notes directory.
