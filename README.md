# WeChat Article Crawler MCP Server

这是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 和 Playwright 的微信公众号文章抓取服务端。它允许 AI 助手（如 Claude, Cline 等）通过自动化浏览器安全地提取微信公众号的最新文章列表。

## 功能特性

- **二维码登录**: 提供 `get_login_qrcode` 工具获取公众号平台的登录二维码。
- **状态检查**: 提供 `check_login_status` 工具确认登录状态。
- **文章搜索**: 提供 `search_wechat_articles` 工具支持根据公众号名称（或微信号）精确搜索并返回最近发布的文章列表（支持分页提取）。

> ⚠️ 注意：使用此工具需要您拥有一个微信公众号的**管理员或运营者账号**，并通过微信扫码登录。

## 安装

1. 克隆本仓库到本地：
   ```bash
   git clone https://github.com/monster-echo/mcp-wechat-article-crawler.git
   cd mcp-wechat-article-crawler
   ```

2. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. 安装 Playwright 浏览器依赖：
   ```bash
   playwright install chromium
   ```

## 在各个 AI 客户端中使用此 MCP

你可以将此 MCP 服务端集成到任何支持 MCP 协议的客户端中。以下是主流客户端的配置方法：

假设你的项目绝对路径为：`/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler`

### 1. Claude Desktop (Mac / Windows)

为了在 Claude Desktop 中使用此 MCP，你需要修改其配置文件。

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

在 `mcpServers` 中添加以下配置：

```json
{
  "mcpServers": {
    "WeChatCrawler": {
      "command": "/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler/.venv/bin/python",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler",
      "env": {
        "PYTHONPATH": "/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler"
      }
    }
  }
}
```

配置完成后，完全重启 Claude Desktop（`Cmd+Q` 通道退出）。随后你会在左下角看到一个小锤子图标，即可通过自然语言让 Claude 帮你抓取微信公众号文章。

### 2. VS Code (Cline / Roo Code)

如果你在 VS Code 中使用 [Cline](https://github.com/cline/cline) 或 [Roo Code](https://github.com/RooVetGit/Roo-Code) 插件：

1. 打开 Cline/Roo Code 的设置页，找到 **MCP Servers**。
2. 点击 **Edit MCP Settings**，这会打开 `cline_mcp_settings.json`（通常位于 `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`）。
3. 添加或更新如下配置：

```json
{
  "mcpServers": {
    "WeChatCrawler": {
      "command": "/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler/.venv/bin/python",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler",
      "env": {
        "PYTHONPATH": "/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler"
      }
    }
  }
}
```

保存文件后，Cline 侧边栏的 MCP 模块会自动重启并加载。你可以直接给 Cline 发指令："请使用 WeChatCrawler 帮我扫码登录微信公众号，然后搜索一下「极客时间」"。

### 3. OpenClaw

在 OpenClaw 中配置 MCP 的方式与前面类似（均基于标准的 JSON 配置或命令行调用）。请在 OpenClaw 的 MCP 接入配置界面或其配置文件中，填写以下参数：

- **Command**: `/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler/.venv/bin/python`
- **Args**: `["-m", "src.server"]`
- **CWD** (启动目录): `/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler`
- **Environment** (环境变量): `{"PYTHONPATH": "/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler"}`

完成添加后，重启 OpenClaw，在其工具列表中即可看到 `get_login_qrcode`, `check_login_status`, 和 `search_wechat_articles`。

### 4. n8n

在 n8n 中（版本 1.74.0 及以上），你可以通过其原生支持的 MCP 功能接入此服务，从而在工作流中直接调用微信公众号文章抓取能力。

1. 打开 n8n 面板，进入左侧菜单的 **Settings** -> **MCP Servers**。
2. 点击 **Add Server** 按钮，填写名称（例如 `WeChatCrawler`）。
3. 配置参数视你的 n8n 部署方式而定：
   - **本地环境部署（推荐，n8n直接运行在主机上）**：
     - **Transport type (连接方式)**：选择 `Command (stdio)`
     - **Command (执行命令)**：填写你的虚拟环境 Python 的绝对路径：`/Volumes/MacMiniDisk/workspace/mcp-wechat-article-crawler/.venv/bin/python`
     - **Arguments (参数)**：填写 `-m` 和 `src.server`（作为两项单独的参数添加）。
   - **Docker 容器部署**：
     由于 Docker 容器内默认没有 Python 和 Playwright，无法直接使用 `Command` 方式调用主机的 Python 脚本。你需要修改 `src/server.py` 的最后一行，使用 SSE 传输层：`mcp.run(transport='sse')` 启动服务，然后在 n8n 中选择 `SSE` 的连接方式并连接内网 IP 与端口。

4. 设置完成后保存。返回工作流 (Workflows) 界面。
5. 在你的节点中添加一个 **Advanced AI Agent** 节点或调用对应的 **Model Context Protocol** 工具，配置好大模型信息。
6. 最后只需要直接给大模型输入提示词：`"请调用 get_login_qrcode 给我微信扫码登录，然后调用 search_wechat_articles 根据我的输入搜文章"` 即可接通全自动工作流！

## 如何运作

1. AI 调用 `get_login_qrcode` -> 你（用户）打开返回的 Base64 图片，用手机微信扫码。
2. AI 循环调用 `check_login_status` 等待你确认登录。
3. 登录成功后，AI 调用 `search_wechat_articles(account_name, max_articles)` 获取文章数据。
4. Playwright 在后台使用长效的 Cookie 数据目录（`.wechat_profile`），无需每次重新扫码（有效期内）。

---
**Disclaimer**: 自动化抓取脚本仅供学习与辅助办公使用，需遵守相关平台的机器人协议。
