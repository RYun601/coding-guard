#!/usr/bin/env python3
"""coding-guard: UTF-8 BOM 检测 — pre 模式拦截写入，post 模式验证磁盘文件"""
import json, sys, os

# 需要检查 BOM 的源码文件扩展名
SRC_EXTS = {'.php', '.js', '.ts', '.jsx', '.tsx', '.css', '.scss', '.less',
            '.html', '.vue', '.svelte', '.py', '.java', '.go', '.rs', '.rb',
            '.swift', '.kt', '.scala', '.sh', '.bash', '.zsh', '.yml', '.yaml',
            '.toml', '.json', '.xml', '.svg', '.sql', '.md', '.cs', '.c', '.cpp',
            '.h', '.hpp', '.ini', '.cfg', '.conf', '.env.example', '.txt'}
BOM = b'\xef\xbb\xbf'


def is_src_file(filepath):
    _, ext = os.path.splitext(filepath) if filepath else ('', '')
    return ext.lower() in SRC_EXTS


def check_content_for_bom(content):
    """检查字符串内容是否以 BOM 开头"""
    if content and content.encode('utf-8').startswith(BOM):
        return True
    # 也检查原始字节（content 可能已含 BOM 字符 U+FEFF）
    if content and ord(content[0]) == 0xFEFF:
        return True
    return False


def check_file_for_bom(filepath):
    """检查磁盘文件是否以 BOM 开头"""
    try:
        with open(filepath, 'rb') as f:
            return f.read(3) == BOM
    except (OSError, IOError):
        return False


def mode_pre(data):
    """PreToolUse: 检查待写入内容"""
    tool_input = data.get('tool_input', {})
    filepath = tool_input.get('file_path', '')

    if not is_src_file(filepath):
        return None  # 非源码文件，跳过

    content = tool_input.get('content', '') or tool_input.get('new_string', '')
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
    """PostToolUse: 验证写入后文件无 BOM"""
    tool_input = data.get('tool_input', {})
    filepath = tool_input.get('file_path', '')

    if not is_src_file(filepath) or not os.path.isfile(filepath):
        return None

    if check_file_for_bom(filepath):
        return json.dumps({
            "systemMessage": f"警告: 文件 {filepath} 已写入但检测到 BOM 头 (EF BB BF)。请立即用 Edit 工具移除以避免后续问题。"
        })
    return None


def main():
    raw = sys.stdin.buffer.read().decode('utf-8')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"systemMessage": "BOM 检查脚本无法解析输入 JSON"}))
        sys.exit(0)

    mode = sys.argv[1] if len(sys.argv) > 1 else 'pre'

    if mode == 'pre':
        result = mode_pre(data)
    elif mode == 'post':
        result = mode_post(data)
    else:
        result = None

    if result:
        print(result)
        if mode == 'pre' and '"permissionDecision":"deny"' in result:
            sys.exit(0)
    sys.exit(0)


if __name__ == '__main__':
    main()
