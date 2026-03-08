import asyncio
import base64
import os
import re
import time
import logging
from playwright.async_api import async_playwright, Page, BrowserContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WechatBrowser:
    def __init__(self):
        self.playwright = None
        self.browser_context: BrowserContext = None  # type: ignore
        self.page: Page = None  # type: ignore
        self.user_data_dir = os.path.join(os.getcwd(), ".wechat_profile")
        self.token = None

    async def start(self):
        # Check if the connection was dropped (e.g. by browserless timeout)
        if (
            hasattr(self, "browser")
            and self.browser
            and not self.browser.is_connected()
        ):
            print("Browser disconnected, stopping and restarting...")
            await self.stop()
            self.playwright = None

        if self.page and self.page.is_closed():
            print("Page closed unexpectedly, stopping and restarting...")
            await self.stop()
            self.playwright = None

        if not self.playwright:
            self.playwright = await async_playwright().start()

            ws_endpoint = os.environ.get("CHROME_WS_ENDPOINT")
            if ws_endpoint:
                print(f"Connecting to remote browser at {ws_endpoint}")
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    ws_endpoint
                )
                # When connecting over CDP, use the default context or create a new one
                self.browser_context = (
                    self.browser.contexts[0]
                    if self.browser.contexts
                    else await self.browser.new_context(
                        viewport={"width": 1280, "height": 800}
                    )
                )
            else:
                self.browser_context = (
                    await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=self.user_data_dir,
                        headless=os.environ.get("HEADLESS", "false").lower() == "true",
                        viewport={"width": 1280, "height": 800},
                    )
                )

            # Use an existing page if available, else create new
            if self.browser_context.pages:
                self.page = self.browser_context.pages[0]
            else:
                self.page = await self.browser_context.new_page()

    async def stop(self):
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_login_qrcode(self) -> str:
        """Navigates to the login page and returns the QR code as a base64 PNG string."""
        await self.start()
        await self.page.goto("https://mp.weixin.qq.com/")

        # Check if already logged in by looking at the URL
        if "cgi-bin/home" in self.page.url:
            return "ALREADY_LOGGED_IN"

        # Wait for the QR code image to appear
        # We must explicitly ensure that the image's src attribute is not empty and contains 'qrcode'
        try:
            qrcode_img = await self.page.wait_for_selector(
                "img.login__type__container__scan__qrcode[src*='qrcode'], .login__qrcode img[src*='qrcode'], img[src*='qrcode']",
                state="visible",
                timeout=15000,
            )
            if qrcode_img:
                # Wait for the image to be fully loaded on the network
                await qrcode_img.evaluate(
                    "img => img.complete || new Promise(resolve => { img.onload = resolve; img.onerror = resolve; })"
                )

                # Verify that it loaded successfully
                is_loaded = await qrcode_img.evaluate("img => img.naturalWidth > 0")
                if not is_loaded:
                    return "Error: QR code image failed to load."

                # take screenshot of the element
                screenshot_bytes = await qrcode_img.screenshot(type="png")
                return base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception as e:
            return f"Error finding QR code: {e}"

        return "QR_CODE_NOT_FOUND"

    async def check_login_status(self) -> str:
        """Checks if the user has successfully logged in."""
        await self.start()

        # If we just started a fresh browser, we might be on about:blank or another blank page.
        # We need to explicitly navigate to the MP site so that the persistent cookies take effect.
        if "mp.weixin.qq.com" not in self.page.url:
            await self.page.goto("https://mp.weixin.qq.com/")

        # Wait a bit to see if navigation/redirect happens
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
        except:
            pass

        url = self.page.url
        if "cgi-bin/home" in url:
            # Extract token
            match = re.search(r"token=(\d+)", url)
            if match:
                self.token = match.group(1)
            return "LOGGED_IN"
        return "NOT_LOGGED_IN"

    async def search_articles(
        self, account_name: str, max_articles: int = 30
    ) -> list[dict]:
        """Searches for articles from a specific official account."""
        if not self.token:
            status = await self.check_login_status()
            if status != "LOGGED_IN":
                raise Exception("Not logged in or token not found.")

        # Navigate to a new draft to open the editor
        # Add a timestamp query param to force the browser to reload instead of skipping navigation
        editor_url = f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&token={self.token}&lang=zh_CN&_t={int(time.time()*1000)}"
        await self.page.goto(editor_url)

        articles = []
        try:
            logger.info(f"开始搜索公众号文章: '{account_name}'")

            # 1. Click '超链接' (Hyperlink) button in the toolbar
            logger.info("正在查找 '超链接' 按钮...")
            await self.page.wait_for_selector("#js_editor_insertlink", timeout=30000)
            # Add no_wait_after=True and force=True to prevent Playwright from deadlocking
            await self.page.click(
                "#js_editor_insertlink", no_wait_after=True, force=True
            )
            logger.info("已点击 '超链接' 按钮。")

            # 2. Wait for the dialog to open, click "其他公众号"
            logger.info("等待超链接对话框打开...")
            dialog_selector = "h3.weui-desktop-dialog__title:has-text('编辑超链接')"
            await self.page.wait_for_selector(
                dialog_selector, state="visible", timeout=10000
            )
            logger.info("对话框已打开。")

            # Click "选择其他账号" if it exists
            btn_selector = "button:has-text('选择其他账号')"
            logger.info("检查是否有 '选择其他账号' 按钮...")
            if await self.page.locator(btn_selector).count() > 0:
                await self.page.click(btn_selector)
                logger.info("已点击 '选择其他账号' 按钮。")
                await self.page.wait_for_timeout(2000)
            else:
                logger.info("未找到 '选择其他账号' 按钮，继续下一步...")

            # Now find the account search input
            logger.info("正在查找账号搜索输入框...")
            account_search_input = (
                "input[placeholder='输入文章来源的账号名称或微信号，回车进行搜索']"
            )
            await self.page.wait_for_selector(
                account_search_input, state="visible", timeout=10000
            )
            await self.page.fill(account_search_input, account_name)
            await self.page.press(account_search_input, "Enter")
            logger.info(f"已输入账号名称 '{account_name}' 并按下回车。")

            # Wait for search results
            await self.page.wait_for_timeout(3000)
            logger.info("已等待 3 秒获取搜索结果。")

            # Try clicking the exact matching account if possible, or fallback to the first result
            # We use a less strict locator because of whitespace and slight name variations
            try:
                logger.info(f"尝试点击完全匹配的账号 '{account_name}'...")
                account_item = self.page.locator(
                    f"li.inner_link_account_item:has(strong.inner_link_account_nickname:has-text('{account_name}'))"
                ).first
                await account_item.wait_for(state="visible", timeout=5000)
                await account_item.click()
                logger.info("已点击完全匹配的账号。")
            except Exception:
                logger.warning(
                    f"完全匹配 '{account_name}' 失败或超时，尝试仅点击第一个搜索结果..."
                )
                # Fallback: Just click the very first account returned by the search
                first_account_item = self.page.locator(
                    "li.inner_link_account_item"
                ).first
                await first_account_item.wait_for(state="visible", timeout=10000)
                await first_account_item.click()
                logger.info("已点击搜索结果中的第一个账号。")

            # Wait for the article list to load
            logger.info("等待文章列表加载...")
            await self.page.wait_for_selector(
                ".inner_link_article_list label.inner_link_article_item", timeout=10000
            )
            logger.info("文章列表已加载。")
            await self.page.wait_for_timeout(
                1000
            )  # give it a moment to render completely

            # Extract articles
            logger.info(f"开始提取文章 (最多 {max_articles} 篇)...")
            while len(articles) < max_articles:
                article_items = await self.page.locator(
                    ".inner_link_article_item"
                ).all()
                current_page_articles = []
                for item in article_items:
                    title_el = item.locator(".inner_link_article_span")
                    link_el = item.locator("a:has-text('查看文章')")

                    if await title_el.count() > 0 and await link_el.count() > 0:
                        title = await title_el.inner_text()
                        url = await link_el.get_attribute("href")
                        current_page_articles.append(
                            {"title": title.strip(), "url": url}
                        )

                # Add to results, preventing exact duplicates
                added_new = False
                for a in current_page_articles:
                    if a not in articles:
                        articles.append(a)
                        added_new = True

                if not added_new or len(articles) >= max_articles:
                    logger.info("已达到目标文章数量或未发现新文章，停止提取。")
                    break

                # Try clicking next page
                # The next page button usually is an `a` tag with text '下一页'
                logger.info("检查是否有 '下一页' 按钮...")
                next_page_btn = self.page.locator("a:has-text('下一页')").first
                if await next_page_btn.count() > 0 and await next_page_btn.is_visible():
                    # Check if disabled
                    btn_class = await next_page_btn.get_attribute("class") or ""
                    if "disabled" in btn_class:  # Could be weui-desktop-btn_disabled
                        logger.info("下一页按钮已被禁用，停止提取。")
                        break
                    await next_page_btn.click()
                    logger.info("已点击 '下一页'。等待新文章加载...")
                    await self.page.wait_for_timeout(2000)
                else:
                    logger.info("未找到 '下一页' 按钮或按钮被隐藏。")
                    break

            articles = articles[:max_articles]
            logger.info(f"成功提取了 {len(articles)} 篇文章！")

            # Try to explicitly close the dialog by finding and clicking the '取消' button
            logger.info("尝试点击 '取消' 按钮关闭弹窗...")
            cancel_btn = self.page.locator("button:has-text('取消')").first
            if await cancel_btn.count() > 0 and await cancel_btn.is_visible():
                await cancel_btn.click(no_wait_after=True, force=True)
                await self.page.wait_for_timeout(1000)

            # Fallback for closing the dialog by pressing Escape to ensure we can search again cleanly
            logger.info("发送 Escape 按键以防弹窗仍未关闭...")
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(1000)
            await self.page.keyboard.press("Escape")
            logger.info("超链接弹窗及搜索过程已结束。")

            return articles
        except Exception as e:
            logger.error(f"文章搜索过程失败: {e}", exc_info=True)
            raise Exception(f"Failed during article search: {e}")

        return articles
