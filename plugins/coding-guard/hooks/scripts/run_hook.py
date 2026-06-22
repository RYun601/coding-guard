#!/usr/bin/env python3
"""Run a coding-guard hook script from the plugin root."""
import os
import subprocess
import sys


ALLOWED_SCRIPTS = {
    "block_dangerous_cmd.py",
    "check_bom.py",
    "check_secrets.py",
    "session_context.py",
}


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    script_name = sys.argv[1]
    if script_name not in ALLOWED_SCRIPTS:
        sys.exit(0)

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(scripts_dir, script_name)
    if not os.path.isfile(script_path):
        sys.exit(0)

    completed = subprocess.run(
        [sys.executable, script_path, *sys.argv[2:]],
        input=sys.stdin.buffer.read(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.stdout:
        sys.stdout.buffer.write(completed.stdout)
    if completed.stderr:
        sys.stderr.buffer.write(completed.stderr)
    sys.exit(completed.returncode)


if __name__ == "__main__":
    main()
