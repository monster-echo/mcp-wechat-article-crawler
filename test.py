import asyncio
from src.browser import WechatBrowser

async def main():
    browser = WechatBrowser()
    
    print("Getting QR Code...")
    qrcode = await browser.get_login_qrcode()
    if qrcode == "ALREADY_LOGGED_IN":
        print("We are already logged in!")
    else:
        print("QR Code Base64 (first 100 chars):", qrcode[:100])
        print("Please scan it.")
        
        while True:
            status = await browser.check_login_status()
            print("Status:", status)
            if status == "LOGGED_IN":
                print("Login successful.")
                break
            await asyncio.sleep(3)
            
    # Try searching
    print("Searching for articles...")
    try:
        articles = await browser.search_articles("桌子的生活观", max_articles=50)
        print(f"Extracted {len(articles)} articles!")
        for a in articles:
            print(f"- {a['title']}: {a['url']}")
    except Exception as e:
        print("Search error:", e)
        
    await browser.stop()

if __name__ == "__main__":
    asyncio.run(main())
