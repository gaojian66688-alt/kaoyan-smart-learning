import os
import sys
from pathlib import Path

# 确保 backend 目录与项目根目录始终包含在 sys.path 中，无论以何种工作目录启动均可正常导入模块
CURRENT_FILE = os.path.abspath(__file__)
APP_DIR = os.path.dirname(CURRENT_FILE)            # .../backend/app
BACKEND_DIR = os.path.dirname(APP_DIR)             # .../backend
ROOT_DIR = os.path.dirname(BACKEND_DIR)            # .../项目根目录

for _p in [BACKEND_DIR, ROOT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

try:
    from app.config import settings
    from app.database import engine, SessionLocal, Base
    from app.api.exams import router as exams_router
    from app.api.practice import router as practice_router
    from app.api.vocabulary import router as vocabulary_router
    from app.api.analysis import router as analysis_router
    from app.api.mistakes import router as mistakes_router
    from app.api.profile import router as profile_router
    from app.data.seed_genuine_exams import seed_database
except ImportError:
    from backend.app.config import settings
    from backend.app.database import engine, SessionLocal, Base
    from backend.app.api.exams import router as exams_router
    from backend.app.api.practice import router as practice_router
    from backend.app.api.vocabulary import router as vocabulary_router
    from backend.app.api.analysis import router as analysis_router
    from backend.app.api.mistakes import router as mistakes_router
    from backend.app.api.profile import router as profile_router
    from backend.app.data.seed_genuine_exams import seed_database

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="考研英语智能学习系统后端 API 服务"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event: ensure database has genuine exam data
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        from app.models.exam import Exam
        if db.query(Exam).count() == 0:
            print("No exams found in database, seeding genuine past exams...")
            seed_database(db)
    finally:
        db.close()

# Include API routers
app.include_router(exams_router, prefix=settings.API_V1_PREFIX)
app.include_router(practice_router, prefix=settings.API_V1_PREFIX)
app.include_router(vocabulary_router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)
app.include_router(mistakes_router, prefix=settings.API_V1_PREFIX)
app.include_router(profile_router, prefix=settings.API_V1_PREFIX)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

# Mount static frontend
env_frontend = os.getenv("FRONTEND_DIR")
FRONTEND_DIR = Path(env_frontend) if env_frontend else Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_frontend_root():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend index.html not found"}
