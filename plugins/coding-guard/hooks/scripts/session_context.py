#!/usr/bin/env python3
"""coding-guard: SessionStart 项目感知 — 读取配置文件和目录结构推断技术栈"""
import json, sys, os

CONFIG_FILES = {
    'composer.json': 'PHP',
    'package.json': 'Node.js',
    'Cargo.toml': 'Rust',
    'go.mod': 'Go',
    'pom.xml': 'Java/Maven',
    'build.gradle': 'Java/Gradle',
    'build.gradle.kts': 'Java/Gradle',
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
    info = {'techs': [], 'frameworks': [], 'versions': {}}

    # 配置文件检测
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
                    info['versions']['php'] = str(php_ver)  # 保留原始约束如 ^7.3|>=7.3
                require = data.get('require', {})
                if any('codeigniter' in pkg.lower() for pkg in require):
                    info['frameworks'].append('CodeIgniter')
                if 'laravel/framework' in require:
                    info['frameworks'].append('Laravel')
                if 'symfony/framework-bundle' in require:
                    info['frameworks'].append('Symfony')

        elif config_file == 'package.json':
            data = read_json(full_path)
            if data:
                node_ver = data.get('engines', {}).get('node', '')
                if node_ver:
                    info['versions']['node'] = str(node_ver)

    # 目录结构检测（独立于配置文件循环，覆盖无 composer.json 的 CI 3 项目）
    if os.path.isdir(os.path.join(cwd, 'system', 'core')):
        if 'CodeIgniter' not in info['frameworks']:
            info['frameworks'].append('CodeIgniter')

    return info


def main():
    raw = sys.stdin.buffer.read().decode('utf-8')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"systemMessage": "项目感知脚本无法解析输入 JSON"}))
        sys.exit(0)

    cwd = data.get('cwd', '')
    project_info = detect_project(cwd)

    if not project_info['techs'] and not project_info['frameworks']:
        sys.exit(0)

    lines = [f"[coding-guard] 检测到项目技术栈:"]
    if project_info['techs']:
        lines.append(f"  语言/运行时: {', '.join(project_info['techs'])}")
    if project_info['frameworks']:
        lines.append(f"  框架: {', '.join(project_info['frameworks'])}")
    if project_info['versions']:
        for k, v in project_info['versions'].items():
            lines.append(f"  {k} 版本约束: {v}")

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": '\n'.join(lines)
        }
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()
