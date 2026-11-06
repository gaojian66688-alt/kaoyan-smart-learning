import fitz
import easyocr
import time

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)
doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf")

# Test cropping top 20% of page 17 (answer sheet)
page = doc.load_page(16) # 0-indexed: page 17
rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.25)
pix = page.get_pixmap(clip=rect, dpi=100)
img_bytes = pix.tobytes("png")

t0 = time.time()
res = reader.readtext(img_bytes, detail=0)
t1 = time.time()
print(f"Elapsed: {t1-t0:.2f}s")
print("OCR Result:", res)
