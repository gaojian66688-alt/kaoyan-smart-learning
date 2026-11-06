import fitz
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)
doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf")

for idx in [1, 17, 33, 49, 65, 81, 97, 113]:
    page = doc.load_page(idx)
    rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.3)
    pix = page.get_pixmap(clip=rect, dpi=80)
    res = reader.readtext(pix.tobytes("png"), detail=0)
    print(f"Index {idx} (p{idx+1}):", " ".join(res))
