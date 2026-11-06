#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR/backend:${PYTHONPATH:-}"

echo "========================================================================="
echo "考研英语智能学习系统 (Kaoyan Smart Learning) —— 快速启动脚本"
echo "========================================================================="

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 python3，请先安装 Python 3.10+。"
    exit 1
fi

echo "[1/2] 检查真题数据库与词库初始化..."
python3 backend/app/data/seed_genuine_exams.py

echo "[2/2] 正在启动 FastAPI 后端与静态前端服务 (http://127.0.0.1:8000)..."
python3 backend/run_server.py
