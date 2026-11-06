import fitz

def check_pattern(pdf_path, name):
    print(f"\n=== {name} ===")
    doc = fitz.open(pdf_path)
    for p in range(0, min(140, len(doc)), 1):
        # We can quickly save thumbnails or check
        pass
    # Let's check pages 1, 17, 33, 49, 65, 81, 97, 113
    for idx in [1, 17, 33, 49, 65, 81, 97, 113]:
        if idx < len(doc):
            pix = doc.load_page(idx).get_pixmap(dpi=50)
            pix.save(f"scratch_pages/{name}_cover_{idx}.png")
    print(f"Done {name}")

check_pattern(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf", "en1_base")
