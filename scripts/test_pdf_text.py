import fitz
import glob
import os

pdf_dir_1 = r"C:\Users\Administrator\Desktop\英语一"
pdf_dir_2 = r"C:\Users\Administrator\Desktop\英语二"

all_pdfs = glob.glob(os.path.join(pdf_dir_1, "*.pdf")) + glob.glob(os.path.join(pdf_dir_2, "*.pdf"))

for p in all_pdfs:
    doc = fitz.open(p)
    text_sample = ""
    for page_idx in range(min(5, len(doc))):
        text_sample += doc[page_idx].get_text()
    print(f"{os.path.basename(p)}: text len in first 5 pages = {len(text_sample)}")
