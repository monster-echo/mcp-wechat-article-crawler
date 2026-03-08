import json
import logging
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent
from .browser import WechatBrowser

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Avoid duplicated logs if already configured elsewhere
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)

# Create FastMCP server
mcp = FastMCP("wechat-article-crawler", host="0.0.0.0", port=8000)

# Global browser instance
browser = WechatBrowser()


@mcp.tool()
async def get_login_qrcode():
    """
    Returns the WeChat Official Account login QR code as a base64 encoded PNG image.
    The user needs to scan this image with their WeChat app to log in.
    If already logged in, returns "ALREADY_LOGGED_IN".
    """
    try:
        logger.info("开始获取微信公众号平台登录二维码...")
        b64_img = await browser.get_login_qrcode()
        if b64_img == "ALREADY_LOGGED_IN":
            logger.info("检测到已登录，无需再次获取二维码。")
            return "ALREADY_LOGGED_IN"
        if b64_img == "QR_CODE_NOT_FOUND" or b64_img.startswith("Error"):
            logger.error(f"获取二维码失败: {b64_img}")
            return f"Failed to get QR code: {b64_img}"

        logger.info("成功获取登录二维码图片数据。")
        return ImageContent(type="image", data=b64_img, mimeType="image/png")
    except Exception as e:
        logger.error(f"获取登录二维码发生异常: {e}", exc_info=True)
        return f"Error: {e}"


@mcp.tool()
async def check_login_status() -> str:
    """
    Checks if the current session is logged into the WeChat Official Account platform.
    Returns "LOGGED_IN" if successful, or "NOT_LOGGED_IN".
    """
    try:
        logger.info("开始检查当前微信公众号平台登录状态...")
        status = await browser.check_login_status()
        logger.info(f"登录状态检查结果: {status}")
        return status
    except Exception as e:
        logger.error(f"检查登录状态时发生异常: {e}", exc_info=True)
        return f"Error checking status: {e}"


@mcp.tool()
async def search_wechat_articles(account_name: str, count: int = 30) -> str:
    """
    Searches for recent articles from the specified WeChat Official Account.
    Returns a list of articles with their titles and URLs.
    You MUST be logged in (scan the QR code first) before calling this.
    `count` specifies the maximum number of articles to return (default 30).
    """
    try:
        logger.info(
            f"收到 MCP 搜索请求！目标公众号: '{account_name}'，预期提取数量: {count}"
        )
        articles = await browser.search_articles(account_name, count)
        if not articles:
            logger.warning(f"未能找到公众号 '{account_name}' 的任何文章。")
            return f"No articles found for '{account_name}' or search failed."

        logger.info(
            f"搜索处理完成，共获取整理 {len(articles)} 篇文章数据，准备返回 JSON。"
        )
        # Format the output as structured JSON
        return json.dumps(
            {"account": account_name, "count": len(articles), "articles": articles},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        logger.error(f"搜索公众号文章发生异常: {e}", exc_info=True)
        return f"Error searching articles: {e}"


if __name__ == "__main__":
    mcp.run(transport="sse")
