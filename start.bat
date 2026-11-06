@echo off
chcp 65001 >nul
echo =========================================================================
echo 考研英语智能学习系统 (Kaoyan Smart Learning) —— 快速启动脚本
echo =========================================================================

REM 检查 Python 环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+ 并添加至系统 PATH。
    pause
    exit /b 1
)

REM 启动本地开发与服务
echo [1/2] 检查真题数据库与词库初始化...
python backend/app/data/seed_genuine_exams.py

echo [2/2] 正在启动 FastAPI 后端与静态前端服务 (http://127.0.0.1:8000)...
python backend/run_server.py
