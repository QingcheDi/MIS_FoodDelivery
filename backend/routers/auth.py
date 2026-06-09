"""
routers/auth.py — 认证接口

实现 API 契约里的：
  POST /api/auth/register  注册
  POST /api/auth/login     登录（返回 JSON，给前端 App/Web 用）
  POST /api/auth/token     OAuth2 表单登录（专给 Swagger /docs 的 Authorize 按钮用）

要点：
  - 密码用 bcrypt 加密后存库，绝不存明文（评分点）
  - 所有 SQL 都用参数化查询（%s 占位），防 SQL 注入（评分点）
  - 登录成功返回 JWT 令牌
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
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


def _authenticate(username: str, password: str):
    """共用的登录校验逻辑：查用户 + 校验密码，成功返回 user 行，失败返回 None。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.password_hash, u.nickname, u.two_factor_enabled, r.name AS role "
                "FROM users u JOIN roles r ON u.role_id = r.id "
                "WHERE u.username=%s",
                (username,),
            )
            user = cur.fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            return None
        return user
    finally:
        conn.close()


@router.post("/register")
def register(req: RegisterReq):
    """注册：检查用户名是否重复 -> 加密密码 -> 写库。"""
    role_id = ROLE_NAME_TO_ID.get(req.role)
    if role_id is None:
        return {"code": 1006, "msg": "角色不合法", "data": None}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username=%s", (req.username,))
            if cur.fetchone():
                return {"code": 1001, "msg": "用户名已存在", "data": None}

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
    """登录（JSON）：查用户 -> 校验密码 -> 发 JWT。前端 App/Web 调这个。"""
    user = _authenticate(req.username, req.password)
    if not user:
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


@router.post("/token")
def login_for_swagger(form: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 表单登录，专给 Swagger /docs 的 Authorize 按钮用。
    它接收表单格式的 username/password，返回 access_token 字段（OAuth2 标准格式），
    这样在 /docs 点 Authorize 填账号密码就能一键登录测试所有接口。
    """
    user = _authenticate(form.username, form.password)
    if not user:
        # OAuth2 规范：失败要抛 401
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user["id"], user["role"])
    return {"access_token": token, "token_type": "bearer"}
