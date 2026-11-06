import fitz
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)
doc = fitz.open(r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典精编版 （2022-2026）.pdf")

for idx, year in zip([15, 31, 47, 63], [2022, 2023, 2024, 2025]):
    page = doc.load_page(idx)
    rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.15)
    pix = page.get_pixmap(clip=rect, dpi=80)
    res = reader.readtext(pix.tobytes("png"), detail=0)
    print(f"EN2 {year} idx {idx}:", " ".join(res))
