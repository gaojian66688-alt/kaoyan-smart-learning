import time
import os
from playwright.sync_api import sync_playwright

def capture_phrase_preview():
    output_dir = r"C:\Users\Administrator\.gemini\antigravity\brain\492a4f9b-15cf-4719-8ccd-a6fc5690823e"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "ui_screen_phrase_optimized.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        
        # 访问练习页
        page.goto("http://127.0.0.1:8000")
        page.wait_for_selector(".home-hero")
        time.sleep(1)
        
        page.click("button[data-view='viewPractice']")
        page.wait_for_selector(".passage-article")
        time.sleep(1)

        # 触发短语弹窗: 打开 "curious treasure"，并在句子中带有 "pull out of" 等搭配
        page.evaluate("""() => {
            // 打开包含智能识别与微调器的短语弹窗
            const para = document.querySelector('.passage-paragraph');
            app.openLookupForText('curious treasure', para, 'In antiquity, the Romans deposited curious treasure here.');
            
            // 同时在文章中将 "curious treasure" 涂上醒目的马克笔高亮
            app.applyMarkerHighlight('curious treasure', true);
            app.applyMarkerHighlight('pull out of', true);
            app.applyMarkerHighlight('handmade nails', true);
            
            // 显示浮动悬浮条在旁边作为操作示意
            const tooltip = document.getElementById('phraseSelectionTooltip');
            if (tooltip) {
                tooltip.style.left = '420px';
                tooltip.style.top = '140px';
                document.getElementById('tooltipPreview').innerText = '"pull out of"';
                tooltip.classList.remove('hidden');
            }
        }""")
        time.sleep(1.2)
        
        page.screenshot(path=out_path)
        print(f"Captured screenshot to: {out_path}")
        browser.close()

if __name__ == "__main__":
    capture_phrase_preview()
