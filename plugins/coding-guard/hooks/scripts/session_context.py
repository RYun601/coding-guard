#!/usr/bin/env python3
"""coding-guard: SessionStart 项目感知 — 读取技术栈配置注入上下文"""
import json, sys, os

# 已知的项目配置文件及其含义
CONFIG_FILES = {
    'composer.json': 'PHP',
    'package.json': 'Node.js',
    'Cargo.toml': 'Rust',
    'go.mod': 'Go',
    'pom.xml': 'Java/Maven',
    'build.gradle': 'Java/Gradle',
    'requirements.txt': 'Python',
    'pyproject.toml': 'Python',
    'Gemfile': 'Ruby',
    'CMakeLists.txt': 'C/C++',
}


def read_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def detect_project(cwd):
    """检测项目技术栈并提取版本约束"""
    info = {'techs': [], 'frameworks': [], 'versions': {}}

    for config_file, tech in CONFIG_FILES.items():
        full_path = os.path.join(cwd, config_file)
        if not os.path.isfile(full_path):
            continue

        info['techs'].append(tech)

        if config_file == 'composer.json':
            data = read_json(full_path)
            if data:
                php_ver = data.get('require', {}).get('php', '')
                if php_ver:
                    info['versions']['php'] = str(php_ver).lstrip('^~>=')
                # 检测框架
                require = data.get('require', {})
                if any('codeigniter' in pkg.lower() for pkg in require):
                    info['frameworks'].append('CodeIgniter')
                if 'laravel/framework' in require:
                    info['frameworks'].append('Laravel')
                if 'symfony/framework-bundle' in require:
                    info['frameworks'].append('Symfony')

        # 额外：通过目录结构检测 CodeIgniter 3.x（system/ 目录在项目根）
        if os.path.isdir(os.path.join(cwd, 'system', 'core')):
            if 'CodeIgniter' not in info['frameworks']:
                info['frameworks'].append('CodeIgniter')

        elif config_file == 'package.json':
            data = read_json(full_path)
            if data:
                node_ver = data.get('engines', {}).get('node', '')
                if node_ver:
                    info['versions']['node'] = str(node_ver).lstrip('^~>=')
    return info


def main():
    raw = sys.stdin.buffer.read().decode('utf-8')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    cwd = data.get('cwd', '')
    project_info = detect_project(cwd)

    if not project_info['techs']:
        sys.exit(0)  # 没有检测到已知项目类型

    # 构建上下文消息
    lines = [f"[coding-guard] 检测到项目技术栈:"]
    lines.append(f"  语言/运行时: {', '.join(project_info['techs'])}")

    if project_info['frameworks']:
        lines.append(f"  框架: {', '.join(project_info['frameworks'])}")

    if project_info['versions']:
        for k, v in project_info['versions'].items():
            lines.append(f"  {k} 版本约束: {v}")

    context_msg = '\n'.join(lines)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context_msg
        }
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()
