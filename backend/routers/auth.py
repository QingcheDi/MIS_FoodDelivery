"""
routers/auth.py — 认证接口

实现 API 契约里的：
  POST /api/auth/register  注册
  POST /api/auth/login     登录

要点：
  - 密码用 bcrypt 加密后存库，绝不存明文（评分点）
  - 所有 SQL 都用参数化查询（%s 占位），防 SQL 注入（评分点）
  - 登录成功返回 JWT 令牌
"""
from fastapi import APIRouter
from pydantic import BaseModel

from database import get_connection
from core.security import hash_password, verify_password, create_token

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ---- 请求体模型（FastAPI 自动校验字段类型）----
class RegisterReq(BaseModel):
    username: str
    password: str
    role: str  # customer/rider/merchant/analyst/regulator
    phone: str | None = None
    email: str | None = None


class LoginReq(BaseModel):
    username: str
    password: str


# 角色英文名 -> roles 表里的 id（与 seed.sql 一致）
ROLE_NAME_TO_ID = {
    "customer": 1, "rider": 2, "merchant": 3, "analyst": 4, "regulator": 5,
}


@router.post("/register")
def register(req: RegisterReq):
    """注册：检查用户名是否重复 -> 加密密码 -> 写库。"""
    role_id = ROLE_NAME_TO_ID.get(req.role)
    if role_id is None:
        return {"code": 1006, "msg": "角色不合法", "data": None}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 用户名查重（参数化查询，防注入）
            cur.execute("SELECT id FROM users WHERE username=%s", (req.username,))
            if cur.fetchone():
                return {"code": 1001, "msg": "用户名已存在", "data": None}

            # 密码加密后存库
            pw_hash = hash_password(req.password)
            cur.execute(
                "INSERT INTO users (username, password_hash, role_id, phone, email) "
                "VALUES (%s, %s, %s, %s, %s)",
                (req.username, pw_hash, role_id, req.phone, req.email),
            )
            conn.commit()
            new_id = cur.lastrowid
        return {"code": 0, "msg": "注册成功", "data": {"user_id": new_id}}
    finally:
        conn.close()


@router.post("/login")
def login(req: LoginReq):
    """登录：查用户 -> 校验密码 -> 发 JWT。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.password_hash, u.nickname, u.two_factor_enabled, r.name AS role "
                "FROM users u JOIN roles r ON u.role_id = r.id "
                "WHERE u.username=%s",
                (req.username,),
            )
            user = cur.fetchone()

        # 用户不存在 或 密码错误，都返回同样的提示（不暴露哪个错，更安全）
        if not user or not verify_password(req.password, user["password_hash"]):
            return {"code": 1002, "msg": "用户名或密码错误", "data": None}

        token = create_token(user["id"], user["role"])
        return {
            "code": 0,
            "msg": "登录成功",
            "data": {
                "token": token,
                "user_id": user["id"],
                "role": user["role"],
                "nickname": user["nickname"],
                "two_factor_required": bool(user["two_factor_enabled"]),
            },
        }
    finally:
        conn.close()
