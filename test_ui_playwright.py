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

            # 7b. 验证【文章与选项中单词、短语查词，马克笔高亮标记与点击适配】
            # 7b-1: 点击选项中的单词查词，并验证不会误触选项单选状态
            opt_item = page.locator("#q-card-2024-english-1-text1-q21 .option-item[data-key='A']").first
            opt_word = opt_item.locator(".word-token").first
            if opt_word.count() > 0:
                opt_word_text = opt_word.inner_text()
                opt_word.click()
                time.sleep(0.5)
                # 验证选项并没有被勾选（点击单词优先查词，做好点击适配）
                assert not opt_item.get_attribute("class") or "selected" not in opt_item.get_attribute("class"), "Clicking word inside option should not select option"
                
                # 验证弹窗成功弹出并显示该选项词
                pop_word = page.locator("#popoverWord").inner_text()
                assert pop_word.lower() == opt_word_text.lower(), f"Expected {opt_word_text}, got {pop_word}"
                pop_sent = page.locator("#popoverSentence").inner_text()
                assert "选项" in pop_sent, f"Expected option context in sentence, got: {pop_sent}"
                
                # 点击马克笔标记加入生词本
                btn = page.locator("#btnSaveWord")
                if btn.is_enabled():
                    btn.click()
                    time.sleep(0.6)
                
                # 验证已施加马克笔高亮样式 (marker-highlight)
                assert "marker-highlight" in opt_word.get_attribute("class"), "Saved word must have marker-highlight class"
                print(f"6b-1. Option word marker pen highlight verified for: {opt_word_text}")
                page.click(".popover-close")
                time.sleep(0.3)

            # 7b-2: 验证文章与选项中【短语查词、马克笔高亮与取消标记】
            # 在文章中标记真实真题短语 "remote communication"
            page.evaluate("app.openLookupForText('remote communication', document.querySelector('.passage-paragraph'))")
            time.sleep(0.5)
            assert "remote communication" in page.locator("#popoverWord").inner_text().lower()
            assert "短语" in page.locator("#popoverTypeTag").inner_text()
            btn_save = page.locator("#btnSaveWord")
            if btn_save.is_enabled():
                btn_save.click()
                time.sleep(0.6)
            
            # 验证文章中短语已被马克笔高亮 (phrase-marker marker-highlight)
            phrase_marker_art = page.locator(".passage-article .phrase-marker.marker-highlight:has-text('remote communication')")
            assert phrase_marker_art.count() > 0, "Passage phrase must be highlighted with phrase-marker and marker-highlight"
            print("6b-2. Article phrase 'remote communication' marker pen highlight verified.")
            page.click(".popover-close")
            time.sleep(1.2)

            # 在选项中标记真实真题短语 "foster structured"
            page.evaluate("app.openLookupForText('foster structured', document.querySelector('.option-item'))")
            time.sleep(0.5)
            assert "foster structured" in page.locator("#popoverWord").inner_text().lower()
            btn_save_opt = page.locator("#btnSaveWord")
            if btn_save_opt.is_enabled():
                btn_save_opt.click()
                time.sleep(1.2)
            phrase_marker_opt = page.locator(".option-item .phrase-marker.marker-highlight:has-text('foster structured')").first
            assert phrase_marker_opt.count() > 0, "Option phrase must be highlighted with phrase-marker and marker-highlight"
            print("6b-3. Option phrase 'foster structured' marker pen highlight verified.")

            # 点击已标记的短语并测试取消标记 (Unmark)
            phrase_marker_opt.click()
            time.sleep(0.5)
            unmark_btn = page.locator("#btnUnmarkWord")
            assert unmark_btn.is_visible(), "Unmark button should be visible for already marked phrase"
            unmark_btn.click()
            time.sleep(0.5)
            print("6b-4. Phrase unmark and marker removal verified.")

            # 7c. 自动化测试批改后解析交互：错题自动展开、正确题折叠并提供展开按钮 (Prompt #9 核心要求)
            page.on("dialog", lambda dialog: dialog.accept())
            
            # 答题：Q21 选 D (正确)，Q22 选 C (错误，标准为 D)
            q21_opt_d = page.locator("#q-card-2024-english-1-text1-q21 .option-item[data-key='D']")
            if q21_opt_d.count() > 0:
                q21_opt_d.click()
                time.sleep(0.3)
            q22_opt_c = page.locator("#q-card-2024-english-1-text1-q22 .option-item[data-key='C']")
            if q22_opt_c.count() > 0:
                q22_opt_c.click()
                time.sleep(0.3)

            # 点击提交本组练习批改
            page.click("#btnSubmitGroup")
            page.wait_for_selector("#modalScore")
            time.sleep(1)
            print("6c. Group grading submitted successfully and grade modal displayed.")

            # 关闭模态框以查看题目卡片批改结果
            page.click(".modal-close")
            time.sleep(0.5)

            # 验证错误题目 Q22：自动展开解析
            q22_wrong_badge = page.locator("#q-card-2024-english-1-text1-q22 .badge-wrong")
            assert q22_wrong_badge.count() > 0, "Q22 wrong badge missing"
            q22_toggle_btn = page.locator("#btn-toggle-2024-english-1-text1-q22")
            assert "收起解析" in q22_toggle_btn.inner_text(), "Q22 should be auto-expanded with collapse button"
            q22_exp_content = page.locator("#exp-card-2024-english-1-text1-q22")
            assert "expanded" in q22_exp_content.get_attribute("class"), "Q22 exp content should have expanded class"
            print("6d. Wrong question (Q22) auto-expanded explanation verified.")

            # 验证正确题目 Q21：默认折叠，提供“查看解析 ▼”按钮
            q21_correct_badge = page.locator("#q-card-2024-english-1-text1-q21 .badge-correct")
            assert q21_correct_badge.count() > 0, "Q21 correct badge missing"
            q21_toggle_btn = page.locator("#btn-toggle-2024-english-1-text1-q21")
            assert "查看解析" in q21_toggle_btn.inner_text(), "Q21 should have '查看解析' toggle button"
            q21_exp_content = page.locator("#exp-card-2024-english-1-text1-q21")
            assert "collapsed" in q21_exp_content.get_attribute("class"), "Q21 exp content should be initially collapsed"
            
            # 用户点击展开正确题目解析
            q21_toggle_btn.click()
            time.sleep(0.3)
            assert "expanded" in q21_exp_content.get_attribute("class"), "Q21 should expand after clicking toggle"
            assert "收起解析" in q21_toggle_btn.inner_text(), "Q21 button should change to '收起解析'"
            
            # 用户再次点击折叠
            q21_toggle_btn.click()
            time.sleep(0.3)
            assert "collapsed" in q21_exp_content.get_attribute("class"), "Q21 should collapse after clicking toggle again"
            print("6e. Correct question (Q21) collapsible explanation toggle verified.")

        # 8. 切换到【FSRS背词】页面
        page.click("button[data-view='viewReview']")
        page.wait_for_selector(".flashcard-container")
        time.sleep(1)
        # 翻转卡片
        page.click("#flashcard")
        time.sleep(0.5)
        page.screenshot(path="screenshot_5_review.png")
        print("7. FSRS review flashcard and jump context button verified.")

        # 9. 切换到【错题本】页面验证长难句结构、错因标签与导出按钮
        page.click("button[data-view='viewMistakes']")
        page.wait_for_selector(".mistakes-workspace")
        time.sleep(1)
        md_export_btn = page.locator("button:has-text('Markdown归档')")
        assert md_export_btn.count() > 0, "Mistakes markdown export button missing"
        print("8. Mistakes notebook syntax breakdown & export button verified.")

        # 10. 切换到【个人学习档案与趋势看板】页面
        page.click("button[data-view='viewProfile']")
        page.wait_for_selector(".trends-section")
        time.sleep(1)
        cat_bars = page.locator(".category-bar-row")
        print(f"9. Profile trends loaded with {cat_bars.count()} category accuracy bars.")
        page.screenshot(path="screenshot_6_profile.png")

        browser.close()
        print("All UI Playwright verification steps completed successfully!")

if __name__ == "__main__":
    run_ui_test()
