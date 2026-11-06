import fitz
import glob
import os

files = {
    "en1_2014_2021": r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(珍藏版)  (2014-2021).pdf",
    "en1_2022_2026": r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(精编版)  (2022-2026).pdf",
    "en2_2007_2013": r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：导学版（2007-2013）.pdf",
    "en2_2014_2021": r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典珍藏版 （2014-2021）.pdf",
    "en2_2022_2026": r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典精编版 （2022-2026）.pdf",
    "en1_writing_40": r"C:\Users\Administrator\Desktop\英语一\考研英语(一)真题学霸狂练 写作真题40篇.pdf",
    "en1_shouyi": r"C:\Users\Administrator\Desktop\英语一\考研英语(一)自测手译本.pdf",
    "en2_shouyi": r"C:\Users\Administrator\Desktop\英语二\考研英语（二）自测手译本：通用版.pdf"
}

for key, path in files.items():
    if os.path.exists(path):
        doc = fitz.open(path)
        print(f"=== {key} ({len(doc)} pages) ===")
        # check page 2, 3
        p2 = doc.load_page(1)
        p3 = doc.load_page(2)
        p2.get_pixmap(dpi=72).save(f"scratch_pages/{key}_p1.png")
        p3.get_pixmap(dpi=72).save(f"scratch_pages/{key}_p2.png")
print("Done extracting sample covers")
