import fitz

doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\考研英语(一)真题学霸狂练 写作真题40篇.pdf")
# Search where each year is in writing_40
for p in range(0, 15):
    pix = doc.load_page(p).get_pixmap(dpi=100)
    pix.save(f"scratch_pages/w40_p{p}.png")
print("Saved 15 pages of writing_40")
