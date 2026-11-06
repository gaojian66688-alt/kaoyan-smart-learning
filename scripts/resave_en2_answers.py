import fitz

# EN2 2014-2021
doc_en2_2 = fitz.open(r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典珍藏版 （2014-2021）.pdf")
for y, idx in zip(range(2014, 2022), [15, 31, 47, 63, 79, 95, 111, 127]):
    doc_en2_2.load_page(idx).get_pixmap(dpi=150).save(f"scratch_answers/en2_{y}_answers.png")
    print(f"EN2 {y} re-saved")

# EN2 2022-2026
doc_en2_3 = fitz.open(r"C:\Users\Administrator\Desktop\英语二\黄皮书考研英语（二）真题：经典精编版 （2022-2026）.pdf")
for y, idx in zip([2022, 2023, 2024, 2025], [15, 31, 47, 63]):
    doc_en2_3.load_page(idx).get_pixmap(dpi=150).save(f"scratch_answers/en2_{y}_answers.png")
    print(f"EN2 {y} re-saved")

print("All EN2 answer pages re-saved successfully!")
