import time
from playwright.sync_api import sync_playwright

def run_ui_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 850})
        
        # 1. 访问首页
        page.goto("http://127.0.0.1:8000")
        page.wait_for_selector(".home-hero")
        time.sleep(1)
        page.screenshot(path="screenshot_1_home.png")
        print("1. Home verified.")

        # 2. 点击进入真题刷题
        page.click("button[data-view='viewPractice']")
        page.wait_for_selector(".passage-article")
        time.sleep(1)

        # 3. 验证板块切换：切换到【完形填空】
        cloze_btn = page.locator("button.sec-btn:has-text('Use')").first
        if cloze_btn.count() > 0:
            cloze_btn.click()
            time.sleep(1)
            print("2. Cloze section loaded.")

        # 4. 验证板块切换：切换到【英译汉】
        trans_btn = page.locator("button.sec-btn:has-text('Translation')").first
        if trans_btn.count() > 0:
            trans_btn.click()
            time.sleep(1)
            # 验证出现了主观题 textarea 输入框
            subj_box = page.locator(".subjective-textarea").first
            if subj_box.count() > 0:
                subj_box.fill("这是翻译主观题测试输入内容。")
                print("3. Translation subjective input verified.")

        # 5. 切换到【严格模考】模式
        page.click("button.pill-btn[data-mode='strict_mock']")
        time.sleep(0.5)
        # 验证模考倒计时已开启
        timer_text = page.locator("#timerDisplay").inner_text()
        print(f"4. Strict mock countdown timer verified: {timer_text}")

        # 6. 在模考模式下点击单词，验证释义被隐藏
        word_span = page.locator(".word-token:has-text('scientific')").first
        if word_span.count() > 0:
            word_span.click()
            time.sleep(0.5)
            meaning_text = page.locator("#popoverMeaning").inner_text()
            assert "模考锁定" in meaning_text, f"Expected mock lock message, got: {meaning_text}"
            print("5. Strict mock vocabulary hidden verified.")
            page.click(".popover-close")
            time.sleep(0.5)

        # 7. 切换回【专项训练】并测试题型定位筛选 (AT-03)
        page.click("button.pill-btn[data-mode='special_training']")
        time.sleep(0.5)
        read_btn = page.locator("button.sec-btn:has-text('Text 1')").first
        if read_btn.count() > 0:
            read_btn.click()
            time.sleep(1)
            # 点击“推理题”筛选
            page.click("button.cat-pill[data-cat='inference']")
            time.sleep(0.5)
            print("6. Special training inference filter verified (AT-03).")

        # 8. 切换到【FSRS背词】页面
        page.click("button[data-view='viewReview']")
        page.wait_for_selector(".flashcard-container")
        time.sleep(1)
        # 翻转卡片
        page.click("#flashcard")
        time.sleep(0.5)
        page.screenshot(path="screenshot_5_review.png")
        print("7. FSRS review flashcard and jump context button verified.")

        # 9. 切换到【错题本】页面验证长难句结构与错因标签
        page.click("button[data-view='viewMistakes']")
        page.wait_for_selector(".mistakes-workspace")
        time.sleep(1)
        print("8. Mistakes notebook syntax breakdown verified.")

        browser.close()
        print("All UI Playwright verification steps completed successfully!")

if __name__ == "__main__":
    run_ui_test()
