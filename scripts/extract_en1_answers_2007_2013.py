import fitz
import os

doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf")
os.makedirs("scratch_answers", exist_ok=True)

years = [2007, 2008, 2009, 2010, 2011, 2012, 2013]
indices = [17, 33, 49, 65, 81, 97, 113]

for y, idx in zip(years, indices):
    page = doc.load_page(idx)
    pix = page.get_pixmap(dpi=150)
    out_path = f"scratch_answers/en1_{y}_answers.png"
    pix.save(out_path)
    print(f"Saved {y} answers to {out_path}")
