import os
import fitz

# Let's inspect scratch_answers directory
ans_files = os.listdir("scratch_answers")
print(f"Total answer images: {len(ans_files)}")
print(sorted(ans_files))
