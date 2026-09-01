import importlib.util
import io
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
            self.assertIn("Todoist queued.", output.getvalue())

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
            self.assertIn("Todoist queued.", output.getvalue())

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
                patch.object(
                    done_task,
                    "log_completed_task_to_todoist",
                    side_effect=RuntimeError("network unavailable"),
                ),
            ):
                done_task.main([done_task.TODOIST_WORKER_ARGUMENT, "finished task"])

            log_text = error_log.read_text(encoding="utf-8")
            self.assertIn("finished task", log_text)
            self.assertIn("network unavailable", log_text)


if __name__ == "__main__":
    unittest.main()
