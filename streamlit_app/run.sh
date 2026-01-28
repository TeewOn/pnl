#!/bin/bash

# P&L 模拟器 Streamlit 启动脚本

cd "$(dirname "$0")"

echo "🚀 启动 P&L 模拟器 (Streamlit)..."
echo ""

# 检查依赖
if ! command -v streamlit &> /dev/null; then
    echo "📦 安装依赖..."
    pip install -r requirements.txt
fi

# 启动 Streamlit
echo "✅ 启动应用..."
echo "   访问: http://localhost:8501"
echo ""

streamlit run app.py
