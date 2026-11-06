import fitz
import easyocr

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)
doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\考研英语(一)自测手译本.pdf")
print("Total pages in shouyi:", len(doc))

# Let's sample page 2, 10, 20, 50, 100, 150, 200, 250, 300
for p in [0, 1, 2, 3, 4, 10, 20, 50]:
    page = doc.load_page(p)
    rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.2)
    pix = page.get_pixmap(clip=rect, dpi=80)
    res = reader.readtext(pix.tobytes("png"), detail=0)
    print(f"Page {p}:", " ".join(res))
