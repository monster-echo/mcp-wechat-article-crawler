import asyncio
import base64
import os
import re
from playwright.async_api import async_playwright, Page, BrowserContext

class WechatBrowser:
    def __init__(self):
        self.playwright = None
        self.browser_context: BrowserContext = None
        self.page: Page = None
        self.user_data_dir = os.path.join(os.getcwd(), ".wechat_profile")
        self.token = None

    async def start(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
            ws_endpoint = os.environ.get("CHROME_WS_ENDPOINT")
            if ws_endpoint:
                print(f"Connecting to remote browser at {ws_endpoint}")
                self.browser = await self.playwright.chromium.connect_over_cdp(ws_endpoint)
                # When connecting over CDP, use the default context or create a new one
                self.browser_context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context(viewport={"width": 1280, "height": 800})
            else:
                self.browser_context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=os.environ.get("HEADLESS", "false").lower() == "true",
                    viewport={"width": 1280, "height": 800}
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
        qr_selector = ".login__type__container__scan__qrcode img"
        # Sometimes it's inside a different structure, let's just look for img with qrcode in src or a known class
        # MP login QR image has class 'login__type__container__scan__qrcode' usually containing an img
        try:
            qrcode_img = await self.page.wait_for_selector(".login__qrcode img, .login__type__container__scan__qrcode img, img[src*='qrcode']", state="visible", timeout=10000)
            if qrcode_img:
                # take screenshot of the element
                screenshot_bytes = await qrcode_img.screenshot(type="png")
                return base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception as e:
            return f"Error finding QR code: {e}"

        return "QR_CODE_NOT_FOUND"

    async def check_login_status(self) -> str:
        """Checks if the user has successfully logged in."""
        await self.start()
        
        # Wait a bit to see if navigation happens
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

    async def search_articles(self, account_name: str, max_articles: int = 30) -> list[dict]:
        """Searches for articles from a specific official account."""
        if not self.token:
            status = await self.check_login_status()
            if status != "LOGGED_IN":
                raise Exception("Not logged in or token not found.")

        # Navigate to a new draft to open the editor
        editor_url = f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&token={self.token}&lang=zh_CN"
        await self.page.goto(editor_url)

        articles = []
        try:
            # 1. Click '超链接' (Hyperlink) button in the toolbar
            await self.page.wait_for_selector("#js_editor_insertlink", timeout=30000)
            await self.page.click("#js_editor_insertlink")

            # 2. Wait for the dialog to open, click "其他公众号"
            dialog_selector = "h3.weui-desktop-dialog__title:has-text('编辑超链接')"
            await self.page.wait_for_selector(dialog_selector, state="visible", timeout=10000)
            
            # Click "选择其他账号" if it exists
            btn_selector = "button:has-text('选择其他账号')"
            if await self.page.locator(btn_selector).count() > 0:
                await self.page.click(btn_selector)
                await self.page.wait_for_timeout(2000)
                
            # Now find the account search input
            account_search_input = "input[placeholder='输入文章来源的账号名称或微信号，回车进行搜索']"
            await self.page.wait_for_selector(account_search_input, state="visible", timeout=10000)
            await self.page.fill(account_search_input, account_name)
            await self.page.press(account_search_input, "Enter")
            
            # Wait for search results
            await self.page.wait_for_timeout(3000)
            
            # Click the exact matching account
            account_item = self.page.locator(f"li.inner_link_account_item:has(strong.inner_link_account_nickname:has-text('{account_name}'))").first
            await account_item.click()
            
            # Wait for the article list to load
            await self.page.wait_for_selector(".inner_link_article_list label.inner_link_article_item", timeout=10000)
            await self.page.wait_for_timeout(1000) # give it a moment to render completely
                
            # Extract articles
            while len(articles) < max_articles:
                article_items = await self.page.locator(".inner_link_article_item").all()
                current_page_articles = []
                for item in article_items:
                    title_el = item.locator(".inner_link_article_span")
                    link_el = item.locator("a:has-text('查看文章')")
                    
                    if await title_el.count() > 0 and await link_el.count() > 0:
                        title = await title_el.inner_text()
                        url = await link_el.get_attribute("href")
                        current_page_articles.append({
                            "title": title.strip(),
                            "url": url
                        })
                
                # Add to results, preventing exact duplicates
                added_new = False
                for a in current_page_articles:
                    if a not in articles:
                        articles.append(a)
                        added_new = True
                
                if not added_new or len(articles) >= max_articles:
                    break
                    
                # Try clicking next page
                # The next page button usually is an `a` tag with text '下一页'
                next_page_btn = self.page.locator("a:has-text('下一页')").first
                if await next_page_btn.count() > 0 and await next_page_btn.is_visible():
                    # Check if disabled
                    btn_class = await next_page_btn.get_attribute("class") or ""
                    if "disabled" in btn_class: # Could be weui-desktop-btn_disabled
                        break
                    await next_page_btn.click()
                    await self.page.wait_for_timeout(2000)
                else:
                    break
            
            articles = articles[:max_articles]
            print(f"Extracted {len(articles)} articles!")
            
            # Close the dialog by pressing Escape to ensure we can search again cleanly
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(1000)
            await self.page.keyboard.press("Escape")
                
            return articles
        except Exception as e:
            raise Exception(f"Failed during article search: {e}")
            
        return articles
