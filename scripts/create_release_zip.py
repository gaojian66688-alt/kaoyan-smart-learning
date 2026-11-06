import os
import zipfile
import shutil

def create_release_archive():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # 输出压缩包路径：同时输出到 Desktop 和当前父级目录
    desktop_dir = os.path.expanduser(r"C:\Users\Administrator\Desktop")
    desktop_zip = os.path.join(desktop_dir, "kaoyan_smart_learning_v1.0.zip")
    parent_zip = os.path.abspath(os.path.join(root_dir, "..", "kaoyan_smart_learning_v1.0.zip"))
    
    print(f"Packaging project from {root_dir}...")
    
    # 过滤排除名单
    EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".system_generated", "backups", "scratch_pages", "scratch_answers"}
    EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd"}

    # 使用临时文件生成 zip
    temp_zip = os.path.join(root_dir, "_temp_release.zip")
    if os.path.exists(temp_zip):
        os.remove(temp_zip)

    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(root_dir):
            # 过滤排除目录 (注意只过滤顶级 data，保留 backend/app/data)
            dirs[:] = [
                d for d in dirs 
                if d not in EXCLUDE_DIRS and not (d == "data" and root == root_dir)
            ]
            
            for file in files:
                if file == "_temp_release.zip" or file.endswith(".zip"):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in EXCLUDE_EXTS:
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, root_dir)
                
                # 放入统一的前缀文件夹 kaoyan_smart_learning/
                archive_name = os.path.join("kaoyan_smart_learning", rel_path)
                zf.write(abs_path, archive_name)

    print("Zip file compressed successfully.")
    
    # 拷贝至桌面和父目录
    shutil.copy2(temp_zip, desktop_zip)
    shutil.copy2(temp_zip, parent_zip)
    os.remove(temp_zip)
    
    desktop_size_mb = os.path.getsize(desktop_zip) / (1024 * 1024)
    print(f"[1] Desktop package: {desktop_zip} ({desktop_size_mb:.2f} MB)")
    print(f"[2] Workspace package: {parent_zip} ({desktop_size_mb:.2f} MB)")

if __name__ == "__main__":
    create_release_archive()
