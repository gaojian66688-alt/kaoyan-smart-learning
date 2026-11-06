import fitz
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)

def check_doc_answers(pdf_path, name, indices):
    print(f"\n=== Checking {name} ===")
    doc = fitz.open(pdf_path)
    for idx in indices:
        if idx < len(doc):
            page = doc.load_page(idx)
            rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.15)
            pix = page.get_pixmap(clip=rect, dpi=80)
            res = reader.readtext(pix.tobytes("png"), detail=0)
            print(f"Index {idx} (p{idx+1}):", " ".join(res))

# 8 years in 2014-2021: 2014 is likely at idx 17 (p18) or idx 16
# Let's test idx 17, 33, 49, 65, 81, 97, 113, 129
check_doc_answers(
    r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(珍藏版)  (2014-2021).pdf",
    "EN1 2014-2021",
    [17, 33, 49, 65, 81, 97, 113, 129]
)

check_doc_answers(
    r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(精编版)  (2022-2026).pdf",
    "EN1 2022-2026",
    [17, 33, 49, 65, 81]
)
