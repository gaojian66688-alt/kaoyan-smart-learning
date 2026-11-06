import fitz

for name, path in [
    ("writing_40", r"C:\Users\Administrator\Desktop\英语一\考研英语(一)真题学霸狂练 写作真题40篇.pdf"),
    ("shouyi_en1", r"C:\Users\Administrator\Desktop\英语一\考研英语(一)自测手译本.pdf"),
    ("shouyi_en2", r"C:\Users\Administrator\Desktop\英语二\考研英语（二）自测手译本：通用版.pdf")
]:
    doc = fitz.open(path)
    for p in range(2, 6):
        doc.load_page(p).get_pixmap(dpi=100).save(f"scratch_pages/{name}_p{p}.png")

print("Saved TOC pages")
