#!/usr/bin/env python3
"""coding-guard: 轻量正则扫描硬编码凭据 — 在 SAST 工具之前做第一道拦截"""
import json, sys, re

# 硬编码凭据模式
SECRET_PATTERNS = [
    # password/passwd/pwd = "something"
    r'(?:password|passwd|pwd)\s*[:=]\s*[\'"][^\'"]{4,}[\'"]',
    # secret = "..."
    r'secret\s*[:=]\s*[\'"][^\'"]{6,}[\'"]',
    # api_key / apikey = "..."
    r'api[_-]?key\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
    # token = "..." (排除明显非凭据的用法如 CSRF token name)
    r'(?:auth[_-]?token|access[_-]?token|bearer[_-]?token)\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
    # Authorization: Bearer / Basic 含长凭据
    r'Authorization\s*:\s*(?:Bearer|Basic)\s+[\'"][^\'"]{16,}[\'"]',
    # JDBC/数据库连接字符串含明文密码
    r'jdbc:.*password=',
    # mysql_connect / mysqli_connect / new PDO 含密码
    r'(?:mysql_connect|mysqli_connect|new\s+PDO)\s*\([^)]*[\'"]\s*,\s*[\'"][^\'"]{3,}[\'"]',
]

# 排除模式 — 明显不是凭据的用法（赋值 null/empty/env/getenv）
EXCLUDE_PATTERNS = [
    r'(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*""\s*""',          # 空密码双引号
    r"(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*''\s*''",          # 空密码单引号
    r'(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*null\b',            # null
    r'(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*(?:env|getenv)',    # 从环境变量获取
    r'(?:password|passwd|pwd|secret|token|api_key)\s*[:=]\s*\$',                 # 引用变量
]


def check_content(content):
    """返回匹配的硬编码凭据列表"""
    if not content:
        return []
    findings = []
    for pattern in SECRET_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            matched_text = match.group(0)
            # 检查是否匹配排除模式
            excluded = False
            for exc_pattern in EXCLUDE_PATTERNS:
                if re.search(exc_pattern, matched_text, re.IGNORECASE):
                    excluded = True
                    break
            if not excluded:
                findings.append(matched_text[:80])
    return findings


def main():
    raw = sys.stdin.buffer.read().decode('utf-8')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = data.get('tool_input', {})
    # 检查 Write 的 content 和 Edit 的 new_string
    content = tool_input.get('content', '') or tool_input.get('new_string', '')
    filepath = tool_input.get('file_path', '')

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

    sys.exit(0)


if __name__ == '__main__':
    main()
