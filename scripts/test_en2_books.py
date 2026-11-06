import fitz
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)

def check_doc(pdf_path, name, indices):
    print(f"\n=== Checking {name} ===")
    doc = fitz.open(pdf_path)
    print("Total pages:", len(doc))
    for idx in indices:
        if idx < len(doc):
            page = doc.load_page(idx)
            rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.15)
            pix = page.get_pixmap(clip=rect, dpi=80)
            res = reader.readtext(pix.tobytes("png"), detail=0)
            print(f"Index {idx} (p{idx+1}):", " ".join(res))

check_doc(
    r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：导学版（2007-2013）.pdf",
    "EN2 2007-2013",
    [15, 16, 17, 31, 32, 33, 47, 48, 49, 63, 64, 65, 79, 80, 81, 95, 96, 97, 111, 112, 113]
)

check_doc(
    r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典珍藏版 （2014-2021）.pdf",
    "EN2 2014-2021",
    [17, 33, 49, 65, 81, 97, 113, 129]
)

check_doc(
    r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典精编版 （2022-2026）.pdf",
    "EN2 2022-2026",
    [17, 33, 49, 65]
)
