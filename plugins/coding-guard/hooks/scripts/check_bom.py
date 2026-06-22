#!/usr/bin/env python3
"""coding-guard: UTF-8 BOM — pre 拦截写入，post 验证磁盘。兼容 Claude Edit/Write 和 Codex apply_patch"""
import json, sys, os
from hook_input import read_stdin, get_file_path, get_content, is_src_file

BOM = b'\xef\xbb\xbf'


def check_content_for_bom(content):
    if content and content.encode('utf-8').startswith(BOM):
        return True
    if content and ord(content[0]) == 0xFEFF:
        return True
    return False


def check_file_for_bom(filepath):
    try:
        with open(filepath, 'rb') as f:
            return f.read(3) == BOM
    except (OSError, IOError):
        return False


def mode_pre(data):
    tool_input = data.get('tool_input', {})
    filepath = get_file_path(tool_input)
    if not is_src_file(filepath):
        return None

    content = get_content(tool_input)
    if check_content_for_bom(content):
        return json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"检测到 UTF-8 BOM 头 (EF BB BF)，文件 {filepath} 禁止写入。请移除 BOM 后重试。"
            }
        })
    return None


def mode_post(data):
    tool_input = data.get('tool_input', {})
    filepath = get_file_path(tool_input)
    if not is_src_file(filepath) or not os.path.isfile(filepath):
        return None
    if check_file_for_bom(filepath):
        return json.dumps({
            "systemMessage": f"警告: 文件 {filepath} 已写入但检测到 BOM 头 (EF BB BF)。请立即用 Edit 工具移除以避免后续问题。"
        })
    return None


def main():
    data = read_stdin()
    if data is None:
        print(json.dumps({"systemMessage": "BOM 检查脚本无法解析输入 JSON"}))
        sys.exit(0)

    mode = sys.argv[1] if len(sys.argv) > 1 else 'pre'
    result = mode_pre(data) if mode == 'pre' else mode_post(data) if mode == 'post' else None

    if result:
        print(result)
    sys.exit(0)


if __name__ == '__main__':
    main()
