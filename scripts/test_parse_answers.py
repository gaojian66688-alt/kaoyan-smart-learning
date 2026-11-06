import fitz
import easyocr
import glob
import re

reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)

def extract_answers_from_image(img_path):
    res = reader.readtext(img_path, detail=0)
    text = " ".join(res)
    print(f"\n--- {img_path} ---")
    print(text[:300])

extract_answers_from_image("scratch_answers/en1_2007_answers.png")
extract_answers_from_image("scratch_answers/en1_2008_answers.png")
extract_answers_from_image("scratch_answers/en1_2010_answers.png")
