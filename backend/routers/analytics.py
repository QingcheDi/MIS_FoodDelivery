"""
routers/analytics.py — 多维数据分析接口（给 Web 端 ECharts 供数）

  GET /api/analytics/sales?dimension=...   多维销量分析
  GET /api/analytics/overview              总览数字（订单数、营业额、用户数等）

对应评分点：数据分析与多维可视化。
分析师(analyst)角色可访问；这里也允许 merchant/regulator 查看。
返回结构统一为 { labels: [...], values: [...] }，前端直接喂给 ECharts。
"""
from fastapi import APIRouter, Depends

from database import get_connection
from core.security import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["数据分析"])

# 允许查看分析的角色
ANALYTICS_ROLES = {"analyst", "merchant", "regulator"}


@router.get("/sales")
def sales_analysis(
    dimension: str = "category",
    start_date: str | None = None,
    end_date: str | None = None,
    user: dict = Depends(get_current_user),
):
    """
    多维销量分析。dimension 可选：
      category —— 按菜品品类统计销量金额
      time     —— 按日期统计每天营业额
      merchant —— 按商家统计营业额
    可选 start_date / end_date 限定时间范围（格式 2026-06-01）。
    """
    if user["role"] not in ANALYTICS_ROLES:
        return {"code": 1005, "msg": "无权限查看数据分析", "data": None}

    # 只统计已完成的订单
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 时间范围过滤条件（参数化）
            date_cond = ""
            params = []
            if start_date:
                date_cond += " AND o.created_at >= %s"
                params.append(start_date + " 00:00:00")
            if end_date:
                date_cond += " AND o.created_at <= %s"
                params.append(end_date + " 23:59:59")

            if dimension == "category":
                sql = (
                    "SELECT m.category AS label, "
                    "SUM(oi.quantity * oi.unit_price) AS value "
                    "FROM orders o "
                    "JOIN order_items oi ON oi.order_id = o.id "
                    "JOIN menu_items m ON oi.menu_item_id = m.id "
                    "WHERE o.status='completed'" + date_cond +
                    " GROUP BY m.category ORDER BY value DESC"
                )
            elif dimension == "time":
                sql = (
                    "SELECT DATE(o.created_at) AS label, "
                    "SUM(o.total_amount) AS value "
                    "FROM orders o "
                    "WHERE o.status='completed'" + date_cond +
                    " GROUP BY DATE(o.created_at) ORDER BY label"
                )
            elif dimension == "merchant":
                sql = (
                    "SELECT u.nickname AS label, "
                    "SUM(o.total_amount) AS value "
                    "FROM orders o "
                    "JOIN users u ON o.merchant_id = u.id "
                    "WHERE o.status='completed'" + date_cond +
                    " GROUP BY u.nickname ORDER BY value DESC"
                )
            else:
                return {"code": 4001, "msg": "dimension 必须是 category/time/merchant", "data": None}

            cur.execute(sql, params)
            rows = cur.fetchall()

        # 拆成 labels + values，方便前端 ECharts 直接用
        labels = [str(r["label"]) for r in rows]
        values = [float(r["value"]) if r["value"] is not None else 0 for r in rows]
        return {
            "code": 0,
            "msg": "success",
            "data": {"dimension": dimension, "labels": labels, "values": values},
        }
    finally:
        conn.close()


@router.get("/overview")
def overview(user: dict = Depends(get_current_user)):
    """总览数字：累计订单数、已完成数、总营业额、用户数。用于看板顶部卡片。"""
    if user["role"] not in ANALYTICS_ROLES:
        return {"code": 1005, "msg": "无权限查看数据分析", "data": None}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total_orders FROM orders")
            total_orders = cur.fetchone()["total_orders"]
            cur.execute("SELECT COUNT(*) AS completed FROM orders WHERE status='completed'")
            completed = cur.fetchone()["completed"]
            cur.execute("SELECT COALESCE(SUM(total_amount),0) AS revenue FROM orders WHERE status='completed'")
            revenue = cur.fetchone()["revenue"]
            cur.execute("SELECT COUNT(*) AS total_users FROM users")
            total_users = cur.fetchone()["total_users"]
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "total_orders": total_orders,
                "completed_orders": completed,
                "total_revenue": float(revenue),
                "total_users": total_users,
            },
        }
    finally:
        conn.close()
