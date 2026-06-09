"""
routers/upload.py — 文件上传接口（硬件 + 非结构化存储）

  POST /api/upload   上传配送照片(相机) / 语音(麦克风)

非结构化存储要点（评分点）：
  - 文件本体写入服务器磁盘的 uploads/ 目录
  - 数据库 delivery_photos 表只存一行元数据 + 文件路径，不存文件本体
硬件对应：
  - file_type=photo 对应相机（骑手送达拍照）
  - file_type=audio 对应麦克风（顾客语音搜索）
"""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form

from database import get_connection
from core.security import get_current_user

router = APIRouter(prefix="/api/upload", tags=["硬件与文件"])

# 上传文件存放的根目录（相对 backend 目录）。已在 .gitignore 排除，不上传 GitHub。
UPLOAD_DIR = "uploads"

# 允许的文件类型
ALLOWED_TYPES = {"photo", "audio"}


@router.post("")
async def upload_file(
    order_id: int = Form(...),
    file_type: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    接收一个文件 + order_id + file_type，存盘并在 delivery_photos 记元数据。
    用 multipart/form-data 格式（文件上传专用）。
    """
    if file_type not in ALLOWED_TYPES:
        return {"code": 3002, "msg": "file_type 必须是 photo 或 audio", "data": None}

    # 1. 按年份分目录存放，文件名用 uuid 防重名
    year = datetime.now().strftime("%Y")
    save_dir = os.path.join(UPLOAD_DIR, year)
    os.makedirs(save_dir, exist_ok=True)

    # 保留原始扩展名（如 .jpg / .mp3）
    ext = os.path.splitext(file.filename or "")[1]
    safe_name = f"order_{order_id}_{uuid.uuid4().hex[:8]}{ext}"
    rel_path = os.path.join(save_dir, safe_name)  # 存进数据库的相对路径

    # 2. 把文件本体写入磁盘
    try:
        content = await file.read()
        with open(rel_path, "wb") as f:
            f.write(content)
    except Exception:
        return {"code": 3001, "msg": "文件保存失败", "data": None}

    # 3. 数据库只存元数据 + 路径（非结构化存储核心）
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO delivery_photos (order_id, file_path, file_type, uploaded_by) "
                "VALUES (%s, %s, %s, %s)",
                (order_id, rel_path, file_type, user["user_id"]),
            )
            conn.commit()
            new_id = cur.lastrowid
        return {
            "code": 0,
            "msg": "上传成功",
            "data": {"id": new_id, "file_path": rel_path, "file_type": file_type},
        }
    finally:
        conn.close()


@router.get("/by-order/{order_id}")
def list_files(order_id: int, user: dict = Depends(get_current_user)):
    """查某订单关联的所有文件元数据（演示时可看上传记录）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, file_path, file_type, uploaded_by, created_at "
                "FROM delivery_photos WHERE order_id=%s ORDER BY id",
                (order_id,),
            )
            rows = cur.fetchall()
        return {"code": 0, "msg": "success", "data": rows}
    finally:
        conn.close()
