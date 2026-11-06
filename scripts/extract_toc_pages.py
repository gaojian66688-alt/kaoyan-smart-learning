import fitz
import os

doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf")
os.makedirs("scratch_pages", exist_ok=True)
for i in range(1, 6):
    page = doc.load_page(i)
    pix = page.get_pixmap(dpi=150)
    pix.save(f"scratch_pages/en1_base_p{i}.png")
print("Saved pages 1-5")
