import fitz

doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf")
for p in [15, 16, 17, 18]:
    pix = doc.load_page(p).get_pixmap(dpi=150)
    pix.save(f"scratch_pages/en1_base_p{p}.png")
print("Saved pages 15-18")
