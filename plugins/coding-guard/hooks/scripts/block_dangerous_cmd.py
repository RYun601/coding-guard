#!/usr/bin/env python3
"""coding-guard: 拦截可能改变编码的写入命令。兼容 Claude Bash/PowerShell 和 Codex"""
import json, sys, re
from hook_input import read_stdin, get_command

# 危险特征：同时满足「写文件」+「源码目标」才拦截
WRITE_ACTIONS = r'Set-Content|Out-File|Add-Content|\[System\.IO\.File\]::Write(?:All(?:Text|Bytes|Lines)?|Lines)|tee\b|>\s*\S|>>\s*\S'

SRC_EXT_PAT = r'\.(?:php|js|ts|jsx|tsx|mjs|cjs|mts|cts|css|scss|less|html|vue|svelte|py|java|go|rs|rb|swift|kt|sql|json|xml|yml|yaml|md|cs|c|cpp|h|hpp|ps1|bat|cmd|proto|graphql)$'


def has_write_action(command):
    return bool(re.search(WRITE_ACTIONS, command, re.IGNORECASE))


def has_src_target(command):
    return bool(re.search(SRC_EXT_PAT, command, re.IGNORECASE))


def main():
    data = read_stdin()
    if data is None:
        sys.exit(0)

    tool_input = data.get('tool_input', {})
    command = get_command(tool_input)

    if not command:
        sys.exit(0)

    # 同时满足「写文件」+「源码目标」才拦截，不再用白名单（白名单过宽会漏）
    if has_write_action(command) and has_src_target(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "此命令可能改变文件编码或引入 BOM。"
                    "禁止使用 Set-Content/Out-File/> /tee/[System.IO.File]::WriteAllText "
                    "等命令写入源码文件。请使用 Edit/Write 工具代替。"
                )
            }
        }))
    sys.exit(0)


if __name__ == '__main__':
    main()
