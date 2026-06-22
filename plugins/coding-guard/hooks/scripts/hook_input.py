#!/usr/bin/env python3
"""coding-guard: 共享 hook 输入适配 — 解耦 Claude/Codex 不同 stdin schema"""
import json, sys, os


def read_stdin():
    """从 stdin 读取 hook JSON，返回 dict"""
    raw = sys.stdin.buffer.read().decode('utf-8')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def get_file_path(tool_input):
    """从 tool_input 中提取目标文件路径（兼容 Claude Write/Edit 和 Codex apply_patch）"""
    for key in ('file_path', 'file', 'path', 'target'):
        val = tool_input.get(key, '')
        if val:
            return val
    return ''


def get_content(tool_input):
    """从 tool_input 中提取待写入内容（兼容多种字段名）"""
    # Claude: content / new_string
    # Codex apply_patch: patch / text / content / new_string / new_str
    for key in ('content', 'new_string', 'patch', 'text', 'new_str'):
        val = tool_input.get(key, '')
        if val:
            return val
    return ''


def get_command(tool_input):
    """从 tool_input 中提取命令文本"""
    for key in ('command', 'cmd', 'shell_command'):
        val = tool_input.get(key, '')
        if val:
            return val
    return ''


def is_src_file(filepath):
    """检查文件是否是需要 BOM/凭据检查的源码类型"""
    SRC_EXTS = {'.php', '.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs', '.mts', '.cts',
                '.css', '.scss', '.less',
                '.html', '.htm', '.vue', '.svelte', '.py', '.pyi', '.pyx',
                '.java', '.go', '.rs', '.rb', '.swift', '.kt', '.kts', '.scala',
                '.sh', '.bash', '.zsh', '.fish',
                '.yml', '.yaml', '.toml', '.json', '.xml', '.svg', '.sql',
                '.md', '.mdx', '.cs', '.c', '.cpp', '.h', '.hpp', '.cc', '.cxx',
                '.ini', '.cfg', '.conf',
                '.ps1', '.bat', '.cmd',
                '.proto', '.graphql', '.gql',
                '.csproj', '.gradle',
                '.env.example', '.env'}
    # 对于无扩展名文件，匹配完整文件名
    BASENAMES = {'Dockerfile', 'Makefile', '.env.example', '.env',
                 'Gemfile', 'Rakefile', 'Vagrantfile'}
    basename = os.path.basename(filepath) if filepath else ''
    if basename in BASENAMES:
        return True
    _, ext = os.path.splitext(filepath) if filepath else ('', '')
    # 特殊处理 .env.example 等双扩展名
    if basename.endswith('.env.example'):
        return True
    return ext.lower() in SRC_EXTS
