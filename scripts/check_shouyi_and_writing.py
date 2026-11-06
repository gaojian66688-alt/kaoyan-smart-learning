import fitz

doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\考研英语(一)自测手译本.pdf")
print("Shouyi en1 pages:", len(doc))
for p in range(0, 5):
    pix = doc.load_page(p).get_pixmap(dpi=100)
    pix.save(f"scratch_pages/en1_shouyi_p{p}.png")

doc2 = fitz.open(r"C:\Users\Administrator\Desktop\英语一\考研英语(一)真题学霸狂练 写作真题40篇.pdf")
print("Writing 40 pages:", len(doc2))
for p in range(0, 5):
    pix = doc2.load_page(p).get_pixmap(dpi=100)
    pix.save(f"scratch_pages/en1_writing_p{p}.png")

print("Saved shouyi and writing sample pages")
