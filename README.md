# coding-guard

通用编码安全守护插件，适用于 Claude Code 和 Codex。

## 功能

- **UTF-8 BOM 检测**: 在 Edit/Write 写入源码文件前拦截 BOM 头，写入后验证文件编码
- **危险命令拦截**: 阻止 `Set-Content`/`Out-File`/`>`/`[System.IO.File]::WriteAllText` 等可能改变编码的写入方式
- **硬编码凭据扫描**: 正则扫描 `password=`/`secret=`/`api_key=`/`token=` 等模式，拦截明文凭据
- **项目技术栈感知**: SessionStart 读取 `composer.json`/`package.json` 自动注入框架和版本信息

## 安装

### 前置条件

- Python 3.6+（`python3` 需在 PATH 中）
- Node.js（Playwright 和 Chrome DevTools MCP 需要 `npx`）

### Claude Code

**方式一：本地 marketplace（推荐）**

1. 在 `~/.claude/settings.json` 注册 marketplace：

```json
{
  "extraKnownMarketplaces": {
    "coding-guard-local": {
      "source": {
        "source": "url",
        "url": "file:///<repo-path>"
      }
    }
  }
}
```

2. 在 Claude Code 中安装：

```
/plugin install coding-guard@coding-guard-local
```

**方式二：开发模式**

```bash
claude --plugin-dir <repo-path>/plugins/coding-guard
```

### Codex

在项目 `.codex/config.toml` 中添加：

```toml
[[extensions]]
path = "<repo-path>/plugins/coding-guard"
```

或从 git 仓库安装（需先推送到远端）：

```toml
[[extensions]]
repo = "https://github.com/<user>/coding-guard.git"
```

Codex 会自动识别 `hooks/hooks-codex.json` 和 `.mcp.json`。

## 结构

```
coding-guard/                    # marketplace 仓库
  .claude-plugin/
    marketplace.json             # marketplace 清单
  plugins/
    coding-guard/                # 插件本体
      .claude-plugin/plugin.json
      hooks/hooks.json           # Claude Code hooks
      hooks/hooks-codex.json     # Codex hooks
      hooks/scripts/             # Python hook 脚本
      skills/coding-standards/   # 编码规范速查技能
      .mcp.json                  # Playwright + Chrome DevTools MCP
```

## 许可

MIT
