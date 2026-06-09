"""
main.py — FastAPI 后端入口

已接入的模块：
  - 健康检查 / 数据库检查（骨架自带）
  - 认证模块   routers/auth.py    （注册、登录、OAuth2 token）
  - 菜单模块   routers/menu.py    （菜单查询）
  - 订单模块   routers/orders.py  （下单、查询、接单、更新状态）
  - 上传模块   routers/upload.py  （配送照片/语音，非结构化存储）

运行方式（在 backend 目录、已激活 venv 的前提下）：
  uvicorn main:app --reload
浏览器打开 http://localhost:8000/docs 查看交互式接口文档。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_connection
from routers import auth, menu, orders, upload

app = FastAPI(title="外卖配送信息系统 API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册各业务模块的路由
app.include_router(auth.router)
app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(upload.router)


@app.get("/api/health")
def health():
    """健康检查：服务正常就返回 ok。"""
    return {"code": 0, "msg": "success", "data": {"status": "ok"}}


@app.get("/api/db-check")
def db_check():
    """数据库连通性检查：连上 MySQL 并数一下用户表行数。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS user_count FROM users")
            row = cur.fetchone()
        return {"code": 0, "msg": "数据库连接成功", "data": row}
    finally:
        conn.close()
