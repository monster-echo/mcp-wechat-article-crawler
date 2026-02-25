from mcp.server.fastmcp import FastMCP
from .browser import WechatBrowser
import asyncio
import os

# Create FastMCP server
mcp = FastMCP("wechat-article-crawler")

# Global browser instance
browser = WechatBrowser()

@mcp.tool()
async def get_login_qrcode() -> str:
    """
    Returns the WeChat Official Account login QR code as a base64 encoded PNG image.
    The user needs to scan this image with their WeChat app to log in.
    If already logged in, returns "ALREADY_LOGGED_IN".
    """
    try:
        b64_img = await browser.get_login_qrcode()
        if b64_img == "ALREADY_LOGGED_IN":
            return "ALREADY_LOGGED_IN"
        if b64_img == "QR_CODE_NOT_FOUND" or b64_img.startswith("Error"):
            return f"Failed to get QR code: {b64_img}"
        
        # We can format it as a markdown image or just return the base64 data URI
        # For an MCP tool, returning the data URI is usually best so the client can render it
        return f"data:image/png;base64,{b64_img}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
async def check_login_status() -> str:
    """
    Checks if the current session is logged into the WeChat Official Account platform.
    Returns "LOGGED_IN" if successful, or "NOT_LOGGED_IN".
    """
    try:
        return await browser.check_login_status()
    except Exception as e:
        return f"Error checking status: {e}"

@mcp.tool()
async def search_wechat_articles(account_name: str) -> str:
    """
    Searches for recent articles from the specified WeChat Official Account.
    Returns a list of articles with their titles and URLs.
    You MUST be logged in (scan the QR code first) before calling this.
    """
    try:
        articles = await browser.search_articles(account_name)
        if not articles:
            return f"No articles found for '{account_name}' or search failed."
        
        # Format the output
        result = [f"Found {len(articles)} articles for {account_name}:"]
        for idx, art in enumerate(articles, 1):
            result.append(f"{idx}. {art.get('title')} - {art.get('url')}")
            
        return "\n".join(result)
    except Exception as e:
        return f"Error searching articles: {e}"

if __name__ == "__main__":
    mcp.run()
