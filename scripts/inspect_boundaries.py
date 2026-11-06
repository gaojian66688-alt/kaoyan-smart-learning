import fitz

doc = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(基础版)（2007-2013）.pdf")
print("Total pages:", len(doc))

# Let's search for "全国硕士研究生招生考试" or "参考答案" in pages
# Wait, it's image PDF, so text search on doc won't work directly, but we can check page boundaries:
# Each exam paper is 1 cover + 14 pages exam + 1 page answers = 16 pages!
# 2007: p2 - p17
# 2008: p18 - p33
# 2009: p34 - p49
# 2010: p50 - p65
# 2011: p66 - p81
# 2012: p82 - p97
# 2013: p98 - p113
# Then at p114+: Detailed explanations (试题精解) for 2007-2013!

for p in [17, 33, 49, 65, 81, 97, 113, 114, 115]:
    pix = doc.load_page(p).get_pixmap(dpi=100)
    pix.save(f"scratch_pages/check_p{p}.png")

print("Saved check pages")
