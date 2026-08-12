#!/usr/bin/env python3

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "thought_log_now.py"


class ThoughtLogNowTests(unittest.TestCase):
    def run_script(self, root, zed_exit=0):
        root = Path(root)
        log_path = root / "thought log.txt"
        args_path = root / "zed-args.txt"
        zed_path = root / "zed-stub"
        zed_path.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$@" > "$THOUGHT_LOG_ZED_ARGS"\n'
            f"exit {zed_exit}\n"
        )
        zed_path.chmod(0o755)

        environment = os.environ.copy()
        environment.update(
            {
                "THOUGHT_LOG_PATH": str(log_path),
                "DAILY_NOTES_PATH": str(root),
                "ZED_CLI": str(zed_path),
                "THOUGHT_LOG_ZED_ARGS": str(args_path),
            }
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            env=environment,
        )
        return result, log_path, args_path

    def test_writes_timestamp_and_opens_root_plus_position(self):
        with tempfile.TemporaryDirectory() as directory:
            result, log_path, args_path = self.run_script(directory)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log_path.exists())
            lines = log_path.read_text().splitlines()
            self.assertRegex(lines[0], r"^\d{1,2}-\d{2}-\d{2}$")
            self.assertEqual(lines[1], "---")
            self.assertRegex(lines[2], r"^\d{1,2}:\d{2} [AP]M - $")
            self.assertEqual(
                args_path.read_text().splitlines(),
                [str(Path(directory)), f"{log_path}:3"],
            )

    def test_replaces_existing_empty_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            first, log_path, _ = self.run_script(directory)
            second, _, _ = self.run_script(directory)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            timestamp_lines = [
                line
                for line in log_path.read_text().splitlines()
                if line.endswith(" - ")
            ]
            self.assertEqual(len(timestamp_lines), 1)

    def test_zed_failure_is_visible_without_losing_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            result, log_path, _ = self.run_script(directory, zed_exit=7)

            self.assertEqual(result.returncode, 1)
            self.assertIn("Could not open thought log in Zed", result.stderr)
            self.assertTrue(log_path.exists())

    def test_cleans_empty_timestamps_from_previous_day(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "thought log.txt"
            log_path.write_text(
                "1-01-20\n"
                "---\n"
                "5:00 PM - \n"
                "\n"
                "\n"
                "4:00 PM - A real entry\n"
                "\n"
                "\n"
                "12-31-19\n"
                "---\n"
                "3:00 PM - \n"
                "\n"
                "\n"
            )
            result, log_path, _ = self.run_script(directory)

            self.assertEqual(result.returncode, 0, result.stderr)
            text = log_path.read_text()
            self.assertIn("Cleaned 1 empty timestamp from 1-01-20", result.stdout)
            self.assertNotIn("5:00 PM -", text)
            self.assertIn("4:00 PM - A real entry", text)
            self.assertIn("3:00 PM -", text)


if __name__ == "__main__":
    unittest.main()
