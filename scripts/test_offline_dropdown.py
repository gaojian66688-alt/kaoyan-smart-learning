from playwright.sync_api import sync_playwright
import time

def test_offline_dropdown():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 850})
        page.goto("http://127.0.0.1:8000")
        page.wait_for_selector(".home-hero")
        
        # 进入练习页
        page.click("button[data-view='viewPractice']")
        page.wait_for_selector("#examSelect")
        time.sleep(1)

        # 选择离线未核验试卷 2023-english-1
        page.select_option("#examSelect", "2023-english-1")
        time.sleep(1)

        # 检查是否展示了合规与版权保护空态提示
        assert page.locator("text=官方历年真题来源核验与知识产权保护").count() > 0
        assert page.locator("text=切换至 2024年英语（一）官方全真试卷").count() > 0
        print("Offline protection empty state verified successfully!")

        # 点击切换回 2024年真题
        page.click("text=切换至 2024年英语（一）官方全真试卷")
        time.sleep(1)
        assert page.locator(".passage-article").count() > 0
        assert page.locator("#examSelect").input_value() == "2024-english-1"
        print("Switched back to 2024 exam verified successfully!")

        browser.close()

if __name__ == "__main__":
    test_offline_dropdown()
