import fitz
import easyocr
import re

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)
doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf")

# Page 17 (index 16) is 2007 answers
page = doc.load_page(16)
pix = page.get_pixmap(dpi=150)
res = reader.readtext(pix.tobytes("png"), detail=0)
print("Total tokens:", len(res))
print("First 30 tokens:", res[:30])
print("\nFull Text:\n", "\n".join(res))
