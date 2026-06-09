"""
routers/menu.py — 菜单接口

  GET /api/menu        获取菜品列表（可按商家、品类筛选）
  GET /api/menu/{id}   查单个菜品详情

菜单查询不强制登录（顾客没登录也能浏览）。
"""
from fastapi import APIRouter

from database import get_connection

router = APIRouter(prefix="/api/menu", tags=["核心业务-菜单"])


@router.get("")
def list_menu(merchant_id: int | None = None, category: str | None = None):
    """获取菜品列表。merchant_id、category 为可选筛选条件。"""
    conn = get_connection()
    try:
        # 动态拼 WHERE 条件，但值始终用参数化（%s），防 SQL 注入
        sql = "SELECT id, merchant_id, name, price, category, image_path, status FROM menu_items WHERE status=1"
        params = []
        if merchant_id is not None:
            sql += " AND merchant_id=%s"
            params.append(merchant_id)
        if category:
            sql += " AND category=%s"
            params.append(category)
        sql += " ORDER BY id"

        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return {"code": 0, "msg": "success", "data": rows}
    finally:
        conn.close()


@router.get("/{item_id}")
def get_menu_item(item_id: int):
    """查单个菜品详情。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, merchant_id, name, price, category, image_path, status "
                "FROM menu_items WHERE id=%s",
                (item_id,),
            )
            row = cur.fetchone()
        if not row:
            return {"code": 4004, "msg": "菜品不存在", "data": None}
        return {"code": 0, "msg": "success", "data": row}
    finally:
        conn.close()
