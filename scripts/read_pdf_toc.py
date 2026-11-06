import fitz
import os
import glob
import sys

sys.stdout.reconfigure(encoding="utf-8")

pdf_dir_1 = r"C:\Users\Administrator\Desktop\英语一"
pdf_dir_2 = r"C:\Users\Administrator\Desktop\英语二"

for pdir in [pdf_dir_1, pdf_dir_2]:
    print("="*50)
    print("Dir:", pdir)
    for f in glob.glob(os.path.join(pdir, "*.pdf")):
        fname = os.path.basename(f)
        try:
            doc = fitz.open(f)
            toc = doc.get_toc()
            print(f"File: {fname}, Pages: {len(doc)}, TOC entries: {len(toc)}")
            if toc:
                for item in toc[:10]:
                    print("  ", item)
        except Exception as e:
            print(f"File: {fname}, Error: {e}")
