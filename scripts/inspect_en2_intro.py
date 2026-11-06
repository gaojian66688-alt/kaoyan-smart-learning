import fitz

doc = fitz.open(r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：导学版（2007-2013）.pdf")
for p in range(0, 10):
    pix = doc.load_page(p).get_pixmap(dpi=72)
    pix.save(f"scratch_pages/en2_intro_p{p}.png")
print("Saved 10 pages of en2_intro")
