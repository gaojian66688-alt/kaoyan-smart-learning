import os
import shutil
import sqlite3
import hashlib
from datetime import datetime, timezone

def backup_database():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "kaoyan_learning.db"))
    backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))
    os.makedirs(backup_dir, exist_ok=True)

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    # 1. 验证源数据库完整性
    print(f"Checking database integrity for {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    res = cur.fetchall()
    conn.close()

    if res != [('ok',)]:
        print("Integrity check failed:", res)
        return False

    # 2. 生成备份文件名并复制
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"kaoyan_learning_{ts}.db")
    shutil.copy2(db_path, backup_file)

    # 3. 计算并校验 SHA-256
    def get_hash(fp):
        h = hashlib.sha256()
        with open(fp, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    src_hash = get_hash(db_path)
    bak_hash = get_hash(backup_file)

    if src_hash != bak_hash:
        print("Checksum mismatch! Backup aborted.")
        return False

    print(f"Backup created successfully: {backup_file}")
    print(f"SHA-256: {bak_hash}")
    return True

if __name__ == "__main__":
    backup_database()
