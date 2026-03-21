from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    )
    page = browser.new_page()

    page.goto('https://www.idictation.cn/main/book', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(3000)

    print('Page title:', page.title())

    # Get rendered text content
    app_text = page.evaluate('''() => {
        const app = document.getElementById("app");
        return app ? app.innerText.substring(0, 3000) : "No app found";
    }''')
    print('App inner text:')
    print(app_text)
    print('---')

    # Look for API calls in network
    # Intercept API responses
    api_data = []
    def handle_response(response):
        url = response.url
        if '/api/' in url or '/book' in url or '/vocab' in url:
            try:
                body = response.text()
                if len(body) < 5000:
                    api_data.append({'url': url, 'body': body})
            except:
                pass

    page.on('response', handle_response)

    # Reload to capture API calls
    page.goto('https://www.idictation.cn/main/book', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)

    print(f'\nIntercepted {len(api_data)} API responses:')
    for item in api_data:
        print(f"\nURL: {item['url']}")
        print(f"Body: {item['body'][:1000]}")

    browser.close()
