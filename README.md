# coding-guard

通用编码安全守护插件，适用于 Claude Code 和 Codex。

## 功能

- **UTF-8 BOM 检测**: 在 Edit/Write/apply_patch 写入源码文件前拦截 BOM 头，写入后验证文件编码
- **危险命令拦截**: 阻止 `Set-Content`/`Out-File`/`>`/`>>`/`tee`/`WriteAllText` 等可能改变编码的写入方式
- **硬编码凭据扫描**: 正则扫描 `password=`/`secret=`/`api_key=`/`token=` 等模式，拦截明文凭据
- **项目技术栈感知**: SessionStart 读取 `composer.json`/`package.json` 和目录结构自动注入框架和版本信息

## 安装

### 前置条件

- Python 3.6+
  - macOS/Linux: `python3` 默认可用
  - Windows: 需确保 `python3` 在 PATH 中，或创建 `python3` → `python` 的 shim（如 `doskey python3=python` 或使用 `py -3` 别名）
- Node.js（Playwright 和 Chrome DevTools MCP 需要 `npx`）

### Claude Code

#### 方式一：本地 marketplace

已注册 `coding-guard-local` marketplace（`~/.claude/settings.json` → `extraKnownMarketplaces`），执行：

```text
/plugin install coding-guard@coding-guard-local
```

#### 方式二：开发模式

```bash
claude --plugin-dir <repo-path>/plugins/coding-guard
```

### Codex

#### 方式一：marketplace

注册 marketplace 后安装：

```bash
codex plugin marketplace add <repo-path>
codex plugin add coding-guard@coding-guard-marketplace
```

#### 方式二：开发模式（Codex）

将插件目录加入 Codex 扩展路径（具体命令取决于 Codex 版本，参考 `codex plugin --help`）。

> 注意：插件中的 `.mcp.json` 为 Claude Code 格式。Codex 如需 MCP 服务器请在项目 `.codex/config.toml` 中单独配置。

## 结构

```
coding-guard/                         # marketplace 仓库
  .claude-plugin/marketplace.json     # Claude marketplace 清单
  .agents/plugins/marketplace.json    # Codex marketplace 清单
  plugins/coding-guard/               # 插件本体
    .claude-plugin/plugin.json        # Claude 插件清单
    .codex-plugin/plugin.json         # Codex 插件清单
    hooks/hooks.json                  # Hook 配置（PascalCase matcher，兼容双平台）
    hooks/scripts/                    # Python hook 脚本（跨平台）
      hook_input.py                   # 共享输入适配层
      check_bom.py                    # BOM 检测
      check_secrets.py                # 凭据扫描
      block_dangerous_cmd.py          # 危险命令拦截
      session_context.py              # 项目技术栈感知
    skills/coding-standards/          # 编码规范速查技能
    .mcp.json                         # MCP 服务器（Claude Code 格式）
```

## 跨平台兼容性

| 平台 | Python 命令 | 已验证 |
|------|------------|--------|
| Windows | `python3`（需确保可用） | 脚本语法通过 |
| macOS | `python3` | 脚本语法通过 |
| Linux | `python3` | 脚本语法通过 |

所有 Python 脚本使用 `os.path.join`、无硬编码路径、无平台分支代码。

## 许可

MIT
