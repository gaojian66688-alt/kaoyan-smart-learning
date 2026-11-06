import os
import sys
import uvicorn

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"Starting Kaoyan English Smart Learning Server on http://{host}:{port} ...")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
