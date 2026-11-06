import fitz
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)
doc = fitz.open(r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典珍藏版 （2014-2021）.pdf")

print("Searching EN2 2014-2021 pages...")
# Let's inspect pages 0 to 25
for p in range(0, 25):
    page = doc.load_page(p)
    rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.15)
    pix = page.get_pixmap(clip=rect, dpi=70)
    res = reader.readtext(pix.tobytes("png"), detail=0)
    res_str = " ".join(res)
    if "答案" in res_str or "试题" in res_str or "2014" in res_str:
        print(f"Page {p+1} (idx {p}): {res_str}")
