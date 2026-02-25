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

## 运行服务 (SSE 模式)

本项目采用了 **SSE (Server-Sent Events) 模式**，这使得你可以将这个 MCP 服务端部署在任何服务器上，并通过 HTTP 协议提供服务。

在服务器上启动服务（使用虚拟环境）：
```bash
source .venv/bin/activate
python -m src.server
```
服务默认会在 `http://0.0.0.0:8000` 启动，并提供 `/sse` 端点。

## 工作流平台接入 (以 n8n 为例)

通过 SSE 模式，像 n8n 这样的平台可以直接通过网络请求接入大模型工作流中。

1. 打开 n8n (版本 >= 1.74.0) 面板，进入左侧菜单的 **Settings** -> **MCP Servers**。
2. 点击 **Add Server** 按钮，填写名称（例如 `WeChatCrawler`）。
3. 配置参数：
   - **Transport type (连接方式)**：选择 `SSE`
   - **URL**：填写你的服务器 IP 和端口，例如：`http://<YOUR_SERVER_IP>:8000/sse`
4. 设置完成后保存。返回工作流 (Workflows) 界面。
5. 在你的节点中添加一个 **Advanced AI Agent** 节点或调用对应的 **Model Context Protocol** 工具，配置好大模型信息。
6. 最后只需要直接给大模型输入提示词：`"请调用 get_login_qrcode 给我微信扫码登录，然后调用 search_wechat_articles 根据我的输入搜文章"` 即可接通全自动抓取工作流！

## IDE 或本地客户端接入 (Cline / OpenClaw)

有些只支持标准输入输出 (stdio) 的本地 IDE 插件（如旧版配置）如果不支持直接连接 SSE 服务器，需要你在本机通过类似 `@modelcontextprotocol/inspector` 的客户端或使用 `mcp-proxy` 桥接工具把 SSE 代理为本地命令行调用。

如果工具（如具有最新版 HTTP/SSE 支持的 OpenClaw 或其他支持网络模式的开发工具）原生支持连接网络 SSE MCP：
1. 找到工具所在界面的 **Add MCP Server**。
2. 将模式指定为 **SSE** 或直接填入 URL：`http://<YOUR_SERVER_IP>:8000/sse`
3. 保存后就能像本地配置一样直接访问。

## 如何运作

1. AI 调用 `get_login_qrcode` -> 返回一个包含 base64 图片的数据，用户在客户端或任何图片查看工具中打开，用手机微信扫码。
2. AI 循环调用 `check_login_status` 等待你确认登录。
3. 登录成功后，AI 调用 `search_wechat_articles(account_name, max_articles)` 获取文章数据。
4. Playwright 在主机的 `.wechat_profile` 目录下使用长效的 Cookie 数据，只要登录状态未过期，后续调用即无需再次扫码。

---
**Disclaimer**: 自动化抓取脚本仅供学习与辅助办公使用，并在调用时请遵循相关平台的机器人协议。
