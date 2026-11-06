import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
conn = sqlite3.connect("backend/kaoyan_learning.db")
c = conn.cursor()
c.execute("SELECT id, exam_type, year, title FROM exams")
for row in c.fetchall():
    print("Exam:", row)

c.execute("""
    SELECT qg.exam_id, qg.group_type, count(q.id) 
    FROM question_groups qg 
    LEFT JOIN questions q ON q.group_id = qg.id 
    GROUP BY qg.exam_id, qg.group_type
""")
for row in c.fetchall():
    print("Groups & Questions:", row)

conn.close()
