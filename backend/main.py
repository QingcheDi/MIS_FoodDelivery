"""
main.py — FastAPI 后端入口

已接入的模块：
  - 健康检查 / 数据库检查（骨架自带）
  - 认证模块 routers/auth.py（注册、登录）

运行方式（在 backend 目录、已激活 venv 的前提下）：
  uvicorn main:app --reload
浏览器打开 http://localhost:8000/docs 查看交互式接口文档。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_connection
from routers import auth

app = FastAPI(title="外卖配送信息系统 API", version="0.2.0")

# 允许前端跨域访问（开发阶段放开，方便移动端/Web 端联调）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册各业务模块的路由
app.include_router(auth.router)


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
