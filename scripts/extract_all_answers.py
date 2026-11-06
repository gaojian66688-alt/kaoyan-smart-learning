import fitz
import os

os.makedirs("scratch_answers", exist_ok=True)

# 1. EN1 2014-2021
doc_en1_2 = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(珍藏版)  (2014-2021).pdf")
for y, idx in zip(range(2014, 2022), [17, 33, 49, 65, 81, 97, 113, 129]):
    doc_en1_2.load_page(idx).get_pixmap(dpi=150).save(f"scratch_answers/en1_{y}_answers.png")
    print(f"EN1 {y} saved")

# 2. EN1 2022-2026
doc_en1_3 = fitz.open(r"C:\Users\Administrator\Desktop\英语一\历年考研英语真题解析及复习思路(精编版)  (2022-2026).pdf")
for y, idx in zip([2022, 2023, 2024, 2025], [17, 33, 49, 65]):
    doc_en1_3.load_page(idx).get_pixmap(dpi=150).save(f"scratch_answers/en1_{y}_answers.png")
    print(f"EN1 {y} saved")

# 3. EN2 2007-2013
doc_en2_1 = fitz.open(r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：导学版（2007-2013）.pdf")
for y, idx in zip(range(2007, 2014), [15, 31, 47, 63, 79, 95, 111]):
    doc_en2_1.load_page(idx).get_pixmap(dpi=150).save(f"scratch_answers/en2_{y}_answers.png")
    print(f"EN2 {y} saved")

# 4. EN2 2014-2021
doc_en2_2 = fitz.open(r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典珍藏版 （2014-2021）.pdf")
for y, idx in zip(range(2014, 2022), [17, 33, 49, 65, 81, 97, 113, 129]):
    doc_en2_2.load_page(idx).get_pixmap(dpi=150).save(f"scratch_answers/en2_{y}_answers.png")
    print(f"EN2 {y} saved")

# 5. EN2 2022-2026
doc_en2_3 = fitz.open(r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典精编版 （2022-2026）.pdf")
for y, idx in zip([2022, 2023, 2024, 2025], [17, 33, 49, 65]):
    doc_en2_3.load_page(idx).get_pixmap(dpi=150).save(f"scratch_answers/en2_{y}_answers.png")
    print(f"EN2 {y} saved")

print("All answer pages extracted successfully!")
