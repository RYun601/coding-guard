#!/usr/bin/env python3
"""coding-guard: 拦截可能改变编码的写入命令。兼容 Claude Bash/PowerShell 和 Codex"""
import json, sys, re
from hook_input import read_stdin, get_command, is_src_file

# 危险特征：同时满足「写文件」+「源码目标」才拦截
WRITE_ACTIONS = r'Set-Content|Out-File|Add-Content|\[System\.IO\.File\]::Write(?:All(?:Text|Bytes|Lines)?|Lines)|tee\b|>\s*\S|>>\s*\S'

REDIRECT_TARGET_RE = re.compile(r'(?:^|[^>])>{1,2}\s*(?P<target>"[^"]+"|\'[^\']+\'|\S+)', re.IGNORECASE)
POWERSHELL_TARGET_RE = re.compile(
    r'\b(?:Set-Content|Out-File|Add-Content)\b(?:\s+-[A-Za-z]+\s+(?:"[^"]+"|\'[^\']+\'|\S+))*\s+(?P<target>"[^"]+"|\'[^\']+\'|\S+)',
    re.IGNORECASE,
)
TEE_TARGET_RE = re.compile(
    r'\btee\b(?:\s+-[A-Za-z]+\s+(?:"[^"]+"|\'[^\']+\'|\S+))*\s+(?P<target>"[^"]+"|\'[^\']+\'|\S+)',
    re.IGNORECASE,
)
DOTNET_WRITE_TARGET_RE = re.compile(
    r'\[System\.IO\.File\]::Write(?:All(?:Text|Bytes|Lines)?|Lines)\s*\(\s*(?P<target>"[^"]+"|\'[^\']+\')',
    re.IGNORECASE,
)


def has_write_action(command):
    return bool(re.search(WRITE_ACTIONS, command, re.IGNORECASE))


def clean_target(raw_target):
    target = raw_target.strip().strip('\'"')
    while target.startswith('&') or target.startswith('>'):
        target = target[1:].strip().strip('\'"')
    return target


def iter_write_targets(command):
    for pattern in (REDIRECT_TARGET_RE, POWERSHELL_TARGET_RE, TEE_TARGET_RE, DOTNET_WRITE_TARGET_RE):
        for match in pattern.finditer(command):
            yield clean_target(match.group('target'))


def has_src_target(command):
    return any(is_src_file(target) for target in iter_write_targets(command))


def main():
    data = read_stdin()
    if data is None:
        print(json.dumps({"systemMessage": "危险命令检查脚本无法解析输入 JSON"}))
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
