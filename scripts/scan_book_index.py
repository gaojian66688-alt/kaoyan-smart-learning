import fitz
import os
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)

def scan_book_years(pdf_path, name):
    print(f"\n=================== Scanning {name} ===================")
    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    
    # Check every page for titles or covers
    # In Huang Pi Shu, exam papers are in the first section (pages 0 ~ 150)
    for p in range(min(150, len(doc))):
        page = doc.load_page(p)
        # Crop top 25% where title appears
        rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.25)
        pix = page.get_pixmap(clip=rect, dpi=80)
        res = reader.readtext(pix.tobytes("png"), detail=0)
        res_str = " ".join(res)
        for year in range(2004, 2027):
            if str(year) in res_str:
                print(f"Page {p+1} (idx {p}): found {year} -> {res_str}")
                break

scan_book_years(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf", "EN1 2007-2013")
