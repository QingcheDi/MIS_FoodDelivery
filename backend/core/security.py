"""
core/security.py — 安全相关工具

集中放置三件事：
  1. 密码加密 / 校验（bcrypt）——对应评分点"密码加密存储"
  2. JWT 令牌的生成与解析——登录后发给前端，之后每个请求带它证明身份
  3. 一个依赖函数 get_current_user——给需要登录的接口校验 token
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# ---- JWT 配置 ----
# SECRET_KEY 用于给令牌签名，绝不能泄露。生产环境应放 .env；演示用默认值即可。
SECRET_KEY = os.getenv("JWT_SECRET", "fooddelivery-demo-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24  # 令牌有效期：24 小时

# 告诉 FastAPI：token 从哪个接口获取（用于 /docs 上的 Authorize 按钮）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


# ============ 密码加密 ============

def hash_password(plain: str) -> str:
    """把明文密码加密成 bcrypt 哈希，用于注册时存库。"""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与数据库里的哈希是否匹配，用于登录。"""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


# ============ JWT 令牌 ============

def create_token(user_id: int, role: str) -> str:
    """登录成功后生成 JWT，内含用户 id、角色和过期时间。"""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """解析并校验 JWT，返回里面的 payload；无效或过期则抛错。"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ============ 登录校验依赖 ============

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    需要登录的接口加上这个依赖，即可自动校验请求头里的 token，
    并拿到当前用户信息 {user_id, role}。token 无效会返回 401。
    """
    credentials_error = HTTPException(status_code=401, detail="未登录或 token 失效")
    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        role = payload.get("role")
        if user_id is None:
            raise credentials_error
        return {"user_id": user_id, "role": role}
    except JWTError:
        raise credentials_error
