"""
routers/orders.py — 订单接口（系统核心业务流程）

  POST /api/orders               顾客下单
  GET  /api/orders               按角色查自己的订单
  GET  /api/orders/{id}          订单详情
  PUT  /api/orders/{id}/accept   骑手接单
  PUT  /api/orders/{id}/status   更新订单状态（商家/骑手）

要点：
  - 所有接口都需要登录（Depends(get_current_user)），从 token 拿到当前用户身份
  - 下单时金额由后端按菜品单价计算，不信任前端传的价格（防篡改）
  - 每次状态变化都往 order_status_log 写流水，可追溯订单生命周期
  - 全程参数化查询防注入
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database import get_connection
from core.security import get_current_user

router = APIRouter(prefix="/api/orders", tags=["核心业务-订单"])


# ---- 请求体模型 ----
class OrderItemReq(BaseModel):
    menu_item_id: int
    quantity: int = 1


class CreateOrderReq(BaseModel):
    merchant_id: int
    items: list[OrderItemReq]
    delivery_address: str
    dest_lat: float | None = None
    dest_lng: float | None = None
    remark: str | None = None


class UpdateStatusReq(BaseModel):
    status: str  # accepted/preparing/delivering/completed/cancelled


# 合法的状态值
VALID_STATUS = {"pending", "accepted", "preparing", "delivering", "completed", "cancelled"}


@router.post("")
def create_order(req: CreateOrderReq, user: dict = Depends(get_current_user)):
    """顾客下单：校验菜品、后端算总价、写订单+明细+状态流水。"""
    if not req.items:
        return {"code": 2004, "msg": "订单不能为空", "data": None}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. 取出所有相关菜品的真实单价（不信任前端传的价格）
            ids = [it.menu_item_id for it in req.items]
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(
                f"SELECT id, price FROM menu_items WHERE id IN ({placeholders})",
                ids,
            )
            price_map = {r["id"]: r["price"] for r in cur.fetchall()}

            # 校验菜品都存在
            for it in req.items:
                if it.menu_item_id not in price_map:
                    return {"code": 2005, "msg": f"菜品 {it.menu_item_id} 不存在", "data": None}

            # 2. 后端计算总金额
            total = sum(price_map[it.menu_item_id] * it.quantity for it in req.items)

            # 3. 写订单主表
            cur.execute(
                "INSERT INTO orders (customer_id, merchant_id, total_amount, status, "
                "delivery_address, dest_lat, dest_lng, remark) "
                "VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s)",
                (user["user_id"], req.merchant_id, total, req.delivery_address,
                 req.dest_lat, req.dest_lng, req.remark),
            )
            order_id = cur.lastrowid

            # 4. 写订单明细（单价快照）
            for it in req.items:
                cur.execute(
                    "INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price) "
                    "VALUES (%s, %s, %s, %s)",
                    (order_id, it.menu_item_id, it.quantity, price_map[it.menu_item_id]),
                )

            # 5. 写状态流水
            cur.execute(
                "INSERT INTO order_status_log (order_id, status, operator_id) VALUES (%s, 'pending', %s)",
                (order_id, user["user_id"]),
            )
            conn.commit()

        return {"code": 0, "msg": "下单成功",
                "data": {"order_id": order_id, "total_amount": float(total), "status": "pending"}}
    finally:
        conn.close()


@router.get("")
def list_orders(status: str | None = None, user: dict = Depends(get_current_user)):
    """按角色查订单：顾客看自己下的，骑手看自己接的，商家看自己店的。"""
    conn = get_connection()
    try:
        sql = ("SELECT id, customer_id, rider_id, merchant_id, total_amount, status, "
               "delivery_address, created_at, completed_at FROM orders WHERE 1=1")
        params = []

        role = user["role"]
        uid = user["user_id"]
        if role == "customer":
            sql += " AND customer_id=%s"; params.append(uid)
        elif role == "rider":
            sql += " AND rider_id=%s"; params.append(uid)
        elif role == "merchant":
            sql += " AND merchant_id=%s"; params.append(uid)
        # analyst/regulator 可看全部，不加过滤

        if status:
            sql += " AND status=%s"; params.append(status)
        sql += " ORDER BY created_at DESC"

        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return {"code": 0, "msg": "success", "data": rows}
    finally:
        conn.close()


@router.get("/{order_id}")
def get_order(order_id: int, user: dict = Depends(get_current_user)):
    """订单详情，含菜品明细。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
            order = cur.fetchone()
            if not order:
                return {"code": 2003, "msg": "订单不存在", "data": None}
            cur.execute(
                "SELECT oi.menu_item_id, m.name, oi.quantity, oi.unit_price "
                "FROM order_items oi JOIN menu_items m ON oi.menu_item_id=m.id "
                "WHERE oi.order_id=%s",
                (order_id,),
            )
            order["items"] = cur.fetchall()
        return {"code": 0, "msg": "success", "data": order}
    finally:
        conn.close()


@router.put("/{order_id}/accept")
def accept_order(order_id: int, user: dict = Depends(get_current_user)):
    """骑手接单：仅当订单还没有骑手时可接。"""
    if user["role"] != "rider":
        return {"code": 1005, "msg": "只有骑手能接单", "data": None}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT rider_id FROM orders WHERE id=%s", (order_id,))
            order = cur.fetchone()
            if not order:
                return {"code": 2003, "msg": "订单不存在", "data": None}
            if order["rider_id"] is not None:
                return {"code": 2001, "msg": "订单已被接单", "data": None}

            # 接单：填骑手、改状态为 delivering
            cur.execute(
                "UPDATE orders SET rider_id=%s, status='delivering' WHERE id=%s",
                (user["user_id"], order_id),
            )
            cur.execute(
                "INSERT INTO order_status_log (order_id, status, operator_id) VALUES (%s, 'delivering', %s)",
                (order_id, user["user_id"]),
            )
            conn.commit()
        return {"code": 0, "msg": "接单成功",
                "data": {"order_id": order_id, "status": "delivering", "rider_id": user["user_id"]}}
    finally:
        conn.close()


@router.put("/{order_id}/status")
def update_status(order_id: int, req: UpdateStatusReq, user: dict = Depends(get_current_user)):
    """更新订单状态（商家出餐、骑手送达等），并记流水。"""
    if req.status not in VALID_STATUS:
        return {"code": 2002, "msg": "非法的订单状态", "data": None}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM orders WHERE id=%s", (order_id,))
            if not cur.fetchone():
                return {"code": 2003, "msg": "订单不存在", "data": None}

            # 完成时记录完成时间（用于时段分析）
            if req.status == "completed":
                cur.execute(
                    "UPDATE orders SET status=%s, completed_at=NOW() WHERE id=%s",
                    (req.status, order_id),
                )
            else:
                cur.execute("UPDATE orders SET status=%s WHERE id=%s", (req.status, order_id))

            cur.execute(
                "INSERT INTO order_status_log (order_id, status, operator_id) VALUES (%s, %s, %s)",
                (order_id, req.status, user["user_id"]),
            )
            conn.commit()
        return {"code": 0, "msg": "状态已更新", "data": {"order_id": order_id, "status": req.status}}
    finally:
        conn.close()
