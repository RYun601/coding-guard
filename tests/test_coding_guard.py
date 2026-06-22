import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "coding-guard"
SCRIPTS_DIR = PLUGIN_ROOT / "hooks" / "scripts"


def run_hook(script_name, payload, *args):
    command = [sys.executable, str(SCRIPTS_DIR / script_name), *args]
    return subprocess.run(
        command,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
    )


def hook_decision(stdout):
    assert stdout, "hook produced no stdout"
    return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]


class CodexMetadataTests(unittest.TestCase):
    def test_codex_manifest_has_required_interface_metadata(self):
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["skills"], "./skills/")
        self.assertNotIn("hooks", manifest)
        self.assertNotIn("mcpServers", manifest)

        interface = manifest["interface"]
        for field in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
        ):
            self.assertIsInstance(interface[field], str)
            self.assertTrue(interface[field].strip())
        self.assertIsInstance(interface["defaultPrompt"], list)
        self.assertTrue(interface["defaultPrompt"])
        self.assertTrue(all(isinstance(item, str) and item.strip() for item in interface["defaultPrompt"]))
        self.assertIsInstance(interface["capabilities"], list)
        self.assertTrue(interface["capabilities"])
        self.assertTrue(all(isinstance(item, str) and item.strip() for item in interface["capabilities"]))

    def test_repo_marketplace_uses_codex_schema(self):
        marketplace = json.loads(
            (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )

        self.assertEqual(marketplace["name"], "coding-guard-marketplace")
        self.assertEqual(marketplace["interface"]["displayName"], "Coding Guard")
        [plugin] = marketplace["plugins"]
        self.assertEqual(plugin["name"], "coding-guard")
        self.assertEqual(plugin["source"], {"source": "local", "path": "./plugins/coding-guard"})
        self.assertEqual(
            plugin["policy"],
            {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        )
        self.assertEqual(plugin["category"], "Productivity")


class HookConfigTests(unittest.TestCase):
    def test_default_hooks_use_shared_plugin_root_entrypoint(self):
        hooks = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        serialized = json.dumps(hooks)

        self.assertIn("run_hook.py", serialized)
        self.assertIn("CLAUDE_PLUGIN_ROOT", serialized)
        self.assertNotIn("${PLUGIN_ROOT}", serialized)

    def test_claude_manifest_uses_claude_specific_hooks(self):
        manifest = json.loads(
            (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude_hooks = json.loads(
            (PLUGIN_ROOT / "hooks" / "hooks.claude.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["hooks"], "./hooks/hooks.claude.json")
        self.assertIn("CLAUDE_PLUGIN_ROOT", json.dumps(claude_hooks))

    def test_claude_hooks_have_command_and_command_windows(self):
        hooks = json.loads(
            (PLUGIN_ROOT / "hooks" / "hooks.claude.json").read_text(encoding="utf-8")
        )
        for event_name, event_hooks in hooks["hooks"].items():
            for group in event_hooks:
                for hook in group["hooks"]:
                    with self.subTest(event=event_name):
                        self.assertIn("command", hook)
                        self.assertIn("commandWindows", hook)

    def test_claude_hooks_use_run_hook_entrypoint(self):
        hooks = json.loads(
            (PLUGIN_ROOT / "hooks" / "hooks.claude.json").read_text(encoding="utf-8")
        )
        for event_name, event_hooks in hooks["hooks"].items():
            for group in event_hooks:
                for hook in group["hooks"]:
                    for key in ("command", "commandWindows"):
                        with self.subTest(event=event_name, key=key):
                            self.assertIn("run_hook.py", hook[key])


class HookBehaviorTests(unittest.TestCase):
    def test_set_content_to_source_file_is_denied_when_content_follows_target(self):
        result = run_hook(
            "block_dangerous_cmd.py",
            {"tool_input": {"command": 'Set-Content demo.php "<?php"'}},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_quoted_redirect_target_is_denied(self):
        result = run_hook(
            "block_dangerous_cmd.py",
            {"tool_input": {"command": 'python gen.py > "demo.php"'}},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_windows_path_redirect_target_is_denied(self):
        result = run_hook(
            "block_dangerous_cmd.py",
            {"tool_input": {"command": r'python gen.py > ".\src\demo.ts"'}},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_secret_scan_reads_command_field_as_patch_content(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": "demo.php",
                    "command": (
                        "*** Begin Patch\n"
                        "*** Add File: demo.php\n"
                        '+password = "abcd1234"\n'
                        "*** End Patch"
                    ),
                }
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_bom_scan_reads_command_field_as_patch_content(self):
        result = run_hook(
            "check_bom.py",
            {
                "tool_input": {
                    "file_path": "demo.php",
                    "command": (
                        "*** Begin Patch\n"
                        "*** Add File: demo.php\n"
                        "+\ufeff<?php echo 1;\n"
                        "*** End Patch"
                    ),
                }
            },
            "pre",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_env_file_not_scanned_for_secrets(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": ".env",
                    "content": 'password = "myrealpass"',
                }
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("deny", result.stdout)

    def test_env_example_file_is_scanned_for_secrets(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": ".env.example",
                    "content": 'password = "myrealpass"',
                }
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_pdo_three_params_with_password_is_denied(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": "demo.php",
                    "content": 'new PDO("mysql:host=localhost", "appuser", "hardpass123")',
                }
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_pdo_two_params_without_password_is_not_denied(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": "demo.php",
                    "content": 'new PDO("mysql:host=localhost", "appuser")',
                }
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("deny", result.stdout)

    def test_mysql_connect_three_params_with_password_is_denied(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": "demo.php",
                    "content": 'mysql_connect("localhost", "root", "hardpass123")',
                }
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_mysql_connect_two_params_without_password_is_not_denied(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": "demo.php",
                    "content": 'mysql_connect("localhost", "root")',
                }
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("deny", result.stdout)

    def test_mysqli_connect_three_params_with_password_is_denied(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": "demo.php",
                    "content": 'mysqli_connect("localhost", "root", "hardpass123")',
                }
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(hook_decision(result.stdout), "deny")

    def test_mysqli_connect_two_params_without_password_is_not_denied(self):
        result = run_hook(
            "check_secrets.py",
            {
                "tool_input": {
                    "file_path": "demo.php",
                    "content": 'mysqli_connect("localhost", "root")',
                }
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("deny", result.stdout)

    def test_malformed_json_outputs_system_message(self):
        scripts = [
            ("check_secrets.py", []),
            ("check_bom.py", ["pre"]),
            ("block_dangerous_cmd.py", []),
            ("session_context.py", []),
        ]
        for script, extra_args in scripts:
            with self.subTest(script=script):
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS_DIR / script), *extra_args],
                    input="not valid json {{{",
                    text=True,
                    capture_output=True,
                    cwd=REPO_ROOT,
                    check=False,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                parsed = json.loads(result.stdout)
                self.assertIn("systemMessage", parsed)


if __name__ == "__main__":
    unittest.main()
