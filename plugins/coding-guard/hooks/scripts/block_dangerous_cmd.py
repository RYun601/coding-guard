#!/usr/bin/env python3
"""coding-guard: 拦截可能改变编码的 PowerShell / Bash 写入命令"""
import json, sys, re

# 危险命令模式 — 可能改变文件编码的写入方式
DANGEROUS_PATTERNS = [
    # PowerShell: Set-Content 写入源码文件
    r'Set-Content\b.*\.(php|js|ts|jsx|tsx|css|html|py|java|go|sql|json|xml|yml|yaml|md|cs)',
    # PowerShell: Out-File 写入源码文件
    r'Out-File\b.*\.(php|js|ts|jsx|tsx|css|html|py|java|go|sql|json|xml|yml|yaml|md|cs)',
    # .NET: WriteAllText 方法
    r'\[System\.IO\.File\]::WriteAllText',
    # Bash/PowerShell: > 重定向到源码文件（排除 git/log 类安全命令）
    r'>\s*\S+\.(php|js|ts|jsx|tsx|css|py|java|go|sql|json|yml|yaml|md|cs)',
    # Bash: tee 写入源码文件
    r'tee\s+.*\.(php|js|ts|jsx|tsx|css|html|py|java|go|sql|json|yml|yaml|md|cs)',
]

# 安全的命令前缀 — 即使包含 > 也不拦截
SAFE_COMMANDS = ['git', 'php -l', 'composer', 'npm ', 'npx ', 'node ',
                 'python', 'phpcs', 'php-cs-fixer', 'prettier', 'eslint']


def is_safe_command(command):
    """检查命令是否属于安全的白名单"""
    cmd_stripped = command.strip()
    for safe in SAFE_COMMANDS:
        if cmd_stripped.startswith(safe):
            return True
    return False


def main():
    raw = sys.stdin.buffer.read().decode('utf-8')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = data.get('tool_input', {})
    command = tool_input.get('command', '')

    if not command or is_safe_command(command):
        sys.exit(0)

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "此命令可能改变文件编码或引入 BOM。"
                        "AGENTS.md 规则禁止使用 Set-Content/Out-File/> /[System.IO.File]::WriteAllText "
                        "等命令写入源码文件。请使用 Claude Code 的 Edit/Write 工具代替。"
                    )
                }
            }))
            sys.exit(0)

    sys.exit(0)


if __name__ == '__main__':
    main()
