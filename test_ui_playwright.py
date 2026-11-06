import time
from playwright.sync_api import sync_playwright

def run_ui_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        # 1. 访问首页
        page.goto("http://127.0.0.1:8000")
        page.wait_for_selector(".home-hero")
        time.sleep(1)
        page.screenshot(path="screenshot_1_home.png")
        print("1. Screenshot 1 Home captured")

        # 2. 点击进入真题刷题
        page.click("button[data-view='viewPractice']")
        page.wait_for_selector(".passage-article")
        time.sleep(1)
        page.screenshot(path="screenshot_2_practice.png")
        print("2. Screenshot 2 Practice captured")

        # 3. 点击文章中的单词触发查词 Popover (例如 'algorithmic')
        word_span = page.locator(".word-token:has-text('algorithmic')").first
        if word_span.count() > 0:
            word_span.click()
            time.sleep(0.5)
            page.screenshot(path="screenshot_3_word_popover.png")
            print("3. Screenshot 3 Word Popover captured")
            # 点击加入生词本
            page.click("#btnSaveWord")
            time.sleep(0.5)

        # 4. 选择 Q21 的选项 B
        q21_b = page.locator("#q-card-2024-en1-q21 .option-item[data-key='B']").first
        if q21_b.count() > 0:
            q21_b.click()
        time.sleep(0.5)
        page.screenshot(path="screenshot_4_option_selected.png")
        print("4. Screenshot 4 Option selected captured")

        # 5. 切换到 FSRS 背词页面
        page.click("button[data-view='viewReview']")
        page.wait_for_selector(".flashcard-container")
        time.sleep(1)
        page.screenshot(path="screenshot_5_review.png")
        print("5. Screenshot 5 Review captured")

        browser.close()

if __name__ == "__main__":
    run_ui_test()
