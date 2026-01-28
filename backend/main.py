"""
P&L Model API Server

启动命令：
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import router

app = FastAPI(
    title="P&L Model API",
    description="P&L（损益）预估模型 API，支持多地区、多维度参数配置的 DAU 和财务模拟",
    version="1.0.0",
)

# CORS 配置，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "pl-model-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
