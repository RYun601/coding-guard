#!/usr/bin/env python3
"""coding-guard: 硬编码凭据扫描。兼容 Claude Edit/Write 和 Codex apply_patch"""
import json, sys, re
from hook_input import read_stdin, get_content, is_src_file, get_file_path

SECRET_PATTERNS = [
    r'(?:password|passwd|pwd)\s*[:=]\s*[\'"][^\'"]{4,}[\'"]',
    r'secret\s*[:=]\s*[\'"][^\'"]{6,}[\'"]',
    r'api[_-]?key\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
    r'(?:auth[_-]?token|access[_-]?token|bearer[_-]?token)\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
    r'Authorization\s*:\s*(?:Bearer|Basic)\s+[\'"][^\'"]{16,}[\'"]',
    r'jdbc:.*password=',
    r'(?:mysql_connect|mysqli_connect|new\s+PDO)\s*\(\s*[\'"][^\'"]*[\'"]\s*,\s*[\'"][^\'"]*[\'"]\s*,\s*[\'"][^\'"]{3,}[\'"]',
]

EXCLUDE_PATTERNS = [
    r'(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*""\s*""',
    r"(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*''\s*''",
    r'(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*null\b',
    r'(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*(?:env|getenv)',
    r'(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*\$',
]


def check_content(content):
    if not content:
        return []
    findings = []
    for pattern in SECRET_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            matched = match.group(0)
            excluded = any(re.search(exc, matched, re.IGNORECASE) for exc in EXCLUDE_PATTERNS)
            if not excluded:
                findings.append(matched[:80])
    return findings


def main():
    data = read_stdin()
    if data is None:
        print(json.dumps({"systemMessage": "凭据检查脚本无法解析输入 JSON"}))
        sys.exit(0)

    tool_input = data.get('tool_input', {})
    filepath = get_file_path(tool_input)
    if not is_src_file(filepath):
        sys.exit(0)

    content = get_content(tool_input)
    findings = check_content(content)
    if findings:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"检测到疑似硬编码凭据: {findings[0]}\n"
                    "AGENTS.md 安全规范要求使用公共变量/常量或环境变量代替硬编码。"
                ),
                "additionalContext": f"发现 {len(findings)} 处疑似凭据: {', '.join(findings[:5])}"
            }
        }))
    sys.exit(0)


if __name__ == '__main__':
    main()
