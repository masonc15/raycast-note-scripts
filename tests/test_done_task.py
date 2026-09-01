import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[1] / "done-task.py"


def load_done_task():
    spec = importlib.util.spec_from_file_location("done_task", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DoneTaskTests(unittest.TestCase):
    def test_entered_task_queues_todoist_after_note_write(self):
        done_task = load_done_task()

        with tempfile.TemporaryDirectory() as directory:
            note_path = Path(directory) / "daily-note.txt"
            note_path.write_text("done\n", encoding="utf-8")

            output = io.StringIO()
            with (
                patch.object(done_task, "get_daily_note_path", return_value=str(note_path)),
                patch.object(done_task, "queue_completed_task_to_todoist") as queue,
                redirect_stdout(output),
            ):
                done_task.main(["finished task"])

            queue.assert_called_once_with("finished task")
            self.assertIn("finished task - ", note_path.read_text(encoding="utf-8"))
            self.assertEqual("Completed: finished task\n", output.getvalue())

    def test_top_now_task_queues_todoist_and_selects_next_task(self):
        done_task = load_done_task()

        with tempfile.TemporaryDirectory() as directory:
            note_path = Path(directory) / "daily-note.txt"
            note_path.write_text(
                "now\n\nfirst task\nsecond task\nlater\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with (
                patch.object(done_task, "get_daily_note_path", return_value=str(note_path)),
                patch.object(done_task, "queue_completed_task_to_todoist") as queue,
                patch.object(done_task, "set_one_thing_task") as set_one_thing,
                redirect_stdout(output),
            ):
                done_task.main([])

            queue.assert_called_once_with("first task")
            set_one_thing.assert_called_once_with("second task")
            note_text = note_path.read_text(encoding="utf-8")
            self.assertNotIn("\nfirst task\n", note_text)
            self.assertIn("first task - ", note_text)
            self.assertEqual("Completed: first task\n", output.getvalue())

    def test_todoist_queue_detaches_worker_output(self):
        done_task = load_done_task()

        with patch.object(done_task.subprocess, "Popen") as popen:
            done_task.queue_completed_task_to_todoist("finished task")

        command = popen.call_args.args[0]
        options = popen.call_args.kwargs
        self.assertEqual(done_task.TODOIST_WORKER_ARGUMENT, command[2])
        self.assertEqual("finished task", command[3])
        self.assertIs(done_task.subprocess.DEVNULL, options["stdin"])
        self.assertIs(done_task.subprocess.DEVNULL, options["stdout"])
        self.assertIs(done_task.subprocess.DEVNULL, options["stderr"])
        self.assertTrue(options["close_fds"])
        self.assertTrue(options["start_new_session"])

    def test_background_worker_records_todoist_failure(self):
        done_task = load_done_task()

        with tempfile.TemporaryDirectory() as directory:
            error_log = Path(directory) / "todoist-worker.log"
            with (
                patch.object(done_task, "TODOIST_ERROR_LOG", str(error_log)),
                patch.object(done_task, "notify_todoist_failure") as notify,
                patch.object(
                    done_task,
                    "log_completed_task_to_todoist",
                    side_effect=RuntimeError("network unavailable"),
                ),
            ):
                done_task.main([done_task.TODOIST_WORKER_ARGUMENT, "finished task"])

            notify.assert_called_once()
            notified_task, notified_error = notify.call_args.args
            self.assertEqual("finished task", notified_task)
            self.assertEqual("network unavailable", str(notified_error))
            log_text = error_log.read_text(encoding="utf-8")
            self.assertIn("finished task", log_text)
            self.assertIn("network unavailable", log_text)

    def test_one_thing_update_does_not_wait_for_open(self):
        done_task = load_done_task()

        with (
            patch.object(
                done_task.subprocess,
                "run",
                side_effect=AssertionError("waited for open"),
            ),
            patch.object(done_task.subprocess, "Popen") as popen,
        ):
            done_task.set_one_thing_task("next & final")

        command = popen.call_args.args[0]
        options = popen.call_args.kwargs
        self.assertEqual(
            ["/usr/bin/open", "--background", "one-thing:?text=next%20%26%20final"],
            command,
        )
        self.assertIs(done_task.subprocess.DEVNULL, options["stdin"])
        self.assertIs(done_task.subprocess.DEVNULL, options["stdout"])
        self.assertIs(done_task.subprocess.DEVNULL, options["stderr"])
        self.assertTrue(options["close_fds"])
        self.assertTrue(options["start_new_session"])

    def test_ui_import_skips_todoist_network_modules(self):
        code = f"""
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("done_task", {str(SCRIPT_PATH)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(" ".join(str(name in sys.modules) for name in (
    "json", "shutil", "urllib.request", "uuid"
)))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual("False False False False", result.stdout.strip())

    def test_todoist_failure_notification_falls_back_to_osascript(self):
        done_task = load_done_task()
        failed = subprocess.CompletedProcess(["terminal-notifier"], 1)
        delivered = subprocess.CompletedProcess(["osascript"], 0)

        with (
            patch.object(done_task, "TERMINAL_NOTIFIER_BINARIES", ("/fake/notifier",)),
            patch.object(done_task.os.path, "isfile", return_value=True),
            patch.object(done_task.os, "access", return_value=True),
            patch.object(
                done_task.subprocess,
                "run",
                side_effect=(failed, delivered),
            ) as run,
        ):
            done_task.notify_todoist_failure(
                "finished task",
                RuntimeError("network unavailable"),
            )

        self.assertEqual(2, run.call_count)
        fallback_command = run.call_args_list[1].args[0]
        self.assertEqual("/usr/bin/osascript", fallback_command[0])
        self.assertIn("finished task", fallback_command)
        self.assertIn("Error: network unavailable", fallback_command)

    def test_sync_task_has_raycast_done_label(self):
        done_task = load_done_task()
        captured_commands = []

        def sync_response(method, url, token, form):
            commands = json.loads(form["commands"])
            captured_commands.extend(commands)
            return {"sync_status": {command["uuid"]: "ok" for command in commands}}

        with patch.object(done_task, "todoist_request", side_effect=sync_response):
            done_task.log_completed_via_sync("finished task", "token")

        add_command = next(
            command for command in captured_commands if command["type"] == "item_add"
        )
        self.assertEqual(
            [done_task.TODOIST_LABEL],
            add_command["args"]["labels"],
        )

    def test_rest_task_has_raycast_done_label(self):
        done_task = load_done_task()
        created_task = {"id": "task-id"}

        with patch.object(
            done_task,
            "todoist_request",
            side_effect=(created_task, None),
        ) as request:
            done_task.log_completed_via_rest("finished task", "token")

        create_call = request.call_args_list[0]
        self.assertEqual(
            [done_task.TODOIST_LABEL],
            create_call.kwargs["payload"]["labels"],
        )

    def test_td_task_has_raycast_done_label(self):
        done_task = load_done_task()
        created = subprocess.CompletedProcess(
            ["td", "task", "add"],
            0,
            stdout='{"id": "task-id"}',
            stderr="",
        )
        completed = subprocess.CompletedProcess(
            ["td", "task", "complete"],
            0,
            stdout="",
            stderr="",
        )

        with (
            patch.object(done_task, "find_td", return_value="/fake/td"),
            patch.object(
                done_task.subprocess,
                "run",
                side_effect=(created, completed),
            ) as run,
        ):
            done_task.log_completed_via_td("finished task")

        add_command = run.call_args_list[0].args[0]
        label_option = add_command.index("--labels")
        self.assertEqual(done_task.TODOIST_LABEL, add_command[label_option + 1])


if __name__ == "__main__":
    unittest.main()
