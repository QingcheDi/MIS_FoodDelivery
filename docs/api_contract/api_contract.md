# API 契约 — 外卖配送信息系统

> 本文件定义前后端之间的**所有接口约定**：每个接口的路径、请求方法、入参、返回格式、状态码。
>
> **作用**：移动端(mobile)、Web 管理端(web)、后端(backend)三方照此并行开发，互不阻塞。前端可先用 Apifox Mock 拿假数据开发，后端按本文件逐个实现真实逻辑。
>
> **配套文档**：字段含义见 `data_dictionary.md`。两份齐全，Phase 0 收尾。

---

## 一、通用约定

### 1.1 基础地址（Base URL）

开发阶段后端跑在本机：

```
http://localhost:8000/api
```

下文所有路径都省略这个前缀，例如 `POST /auth/login` 实际是 `POST http://localhost:8000/api/auth/login`。

### 1.2 统一响应格式

**所有接口**的返回都包成同一个结构，前端只需固定地解析这三个字段：

```json
{
  "code": 0,
  "msg": "success",
  "data": { }
}
```

- `code`：业务状态码。`0` 表示成功；非 0 表示出错（见第五节错误码表）。
- `msg`：给人看的提示文字。
- `data`：真正的数据负载，可能是对象、数组或 null。

> 注意：`code` 是**业务码**，和下面的 **HTTP 状态码**是两回事。HTTP 状态码由协议层返回（200/401/404…），`code` 由我们自己定义。一般成功时 HTTP=200 且 code=0。

### 1.3 认证方式（JWT）

除登录、注册外，**所有接口都需要带令牌**。登录成功后后端返回一个 `token`，前端把它放在每个请求的请求头里：

```
Authorization: Bearer <token>
```

后端校验 token，解析出当前用户身份和角色，再判断是否有权限调用该接口。

### 1.4 时间格式

统一用 ISO 8601 字符串：`2026-06-08T17:30:00`。

---

## 二、认证模块 `/auth`

### 2.1 注册

```
POST /auth/register
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名 |
| password | string | 是 | 明文密码（后端收到后用 bcrypt 加密存储，绝不存明文） |
| role | string | 是 | 角色：customer/rider/merchant/analyst/regulator |
| phone | string | 否 | 手机号 |
| email | string | 否 | 邮箱 |

**成功响应 (HTTP 200)：**

```json
{ "code": 0, "msg": "注册成功", "data": { "user_id": 12 } }
```

**失败示例：** 用户名已存在 → HTTP 200, `{ "code": 1001, "msg": "用户名已存在", "data": null }`

---

### 2.2 登录

```
POST /auth/login
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名 |
| password | string | 是 | 明文密码 |

**成功响应：**

```json
{
  "code": 0,
  "msg": "登录成功",
  "data": {
    "token": "eyJhbGciOiJ...",
    "user_id": 12,
    "role": "customer",
    "nickname": "小明",
    "two_factor_required": false
  }
}
```

> 若该用户开启了两步验证，`two_factor_required` 返回 `true`，此时前端需跳转到 2.3 输入验证码，**暂不发 token**。

**失败示例：** 密码错误 → `{ "code": 1002, "msg": "用户名或密码错误", "data": null }`（HTTP 401）

---

### 2.3 两步验证（验证码校验）

```
POST /auth/2fa/verify
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| user_id | int | 是 | 登录接口返回的 user_id |
| code | string | 是 | 6 位验证码（演示时可 mock 为固定值如 `123456`） |

**成功响应：** 同 2.2，返回 `token`。

---

### 2.4 密码找回

```
POST /auth/recover
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| email | string | 二选一 | 通过邮箱找回 |
| phone | string | 二选一 | 通过手机找回 |

**成功响应：**

```json
{ "code": 0, "msg": "重置链接/验证码已发送（演示为 mock）", "data": null }
```

---

### 2.5 微信登录（OAuth，可 mock）

```
POST /auth/wechat
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| wechat_code | string | 是 | 微信授权码（演示时可 mock） |

**成功响应：** 同 2.2，返回 `token`、`role` 等。

---

## 三、核心业务模块

### 3.1 获取菜单列表

```
GET /menu
```

**查询参数（可选）：**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| merchant_id | int | 只看某商家的菜品 |
| category | string | 按品类筛选 |

**成功响应：**

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    { "id": 3, "name": "黄焖鸡米饭", "price": 22.00, "category": "正餐", "image_path": "uploads/menu/3.jpg", "merchant_id": 5 },
    { "id": 7, "name": "珍珠奶茶", "price": 12.00, "category": "饮品", "image_path": "uploads/menu/7.jpg", "merchant_id": 5 }
  ]
}
```

---

### 3.2 创建订单（顾客下单）

```
POST /orders
```
**权限：** customer

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| merchant_id | int | 是 | 出餐商家 |
| items | array | 是 | 菜品清单，见下 |
| delivery_address | string | 是 | 配送地址 |
| dest_lat | number | 否 | 目的地纬度（GPS） |
| dest_lng | number | 否 | 目的地经度（GPS） |
| remark | string | 否 | 备注（如语音搜索转写的需求） |

`items` 数组每一项：

```json
{ "menu_item_id": 3, "quantity": 2 }
```

**请求示例：**

```json
{
  "merchant_id": 5,
  "items": [ { "menu_item_id": 3, "quantity": 2 }, { "menu_item_id": 7, "quantity": 1 } ],
  "delivery_address": "XX 大学 3 号宿舍楼",
  "dest_lat": 31.2304000,
  "dest_lng": 121.4737000,
  "remark": "不要辣"
}
```

**成功响应：**

```json
{
  "code": 0,
  "msg": "下单成功",
  "data": { "order_id": 1001, "total_amount": 56.00, "status": "pending" }
}
```

---

### 3.3 查询订单列表

```
GET /orders
```
**权限：** 登录用户。后端根据当前角色自动过滤：顾客看自己下的、骑手看自己接的、商家看自己店的。

**查询参数（可选）：**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| status | string | 按状态筛选，如 `pending` |

**成功响应：**

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "id": 1001, "status": "pending", "total_amount": 56.00,
      "delivery_address": "XX 大学 3 号宿舍楼",
      "created_at": "2026-06-08T17:30:00",
      "items": [ { "name": "黄焖鸡米饭", "quantity": 2, "unit_price": 22.00 } ]
    }
  ]
}
```

---

### 3.4 查询单个订单详情

```
GET /orders/{order_id}
```

**成功响应：** 单个订单对象，结构同上，额外含 `rider_id`、`merchant_id`、状态流水等。

---

### 3.5 骑手接单

```
PUT /orders/{order_id}/accept
```
**权限：** rider

**请求体：** 无（骑手身份从 token 解析）。

**成功响应：**

```json
{ "code": 0, "msg": "接单成功", "data": { "order_id": 1001, "status": "delivering", "rider_id": 8 } }
```

**失败示例：** 订单已被别人接 → `{ "code": 2001, "msg": "订单已被接单", "data": null }`

---

### 3.6 更新订单状态

```
PUT /orders/{order_id}/status
```
**权限：** 商家(出餐相关) / 骑手(配送相关)，后端校验。

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| status | string | 是 | 目标状态：accepted/preparing/delivering/completed/cancelled |

**成功响应：**

```json
{ "code": 0, "msg": "状态已更新", "data": { "order_id": 1001, "status": "completed" } }
```

> 每次状态变更，后端自动往 `order_status_log` 写一条流水，可追溯订单生命周期。

---

## 四、硬件与文件上传

### 4.1 上传配送文件（照片 / 语音）

```
POST /upload
```
**权限：** 登录用户（通常是骑手送达拍照、顾客语音搜索）。
**请求格式：** `multipart/form-data`（文件上传专用格式，不是 JSON）。

**表单字段：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | file | 是 | 图片或音频文件本体 |
| order_id | int | 是 | 关联订单 |
| file_type | string | 是 | `photo`(相机) / `audio`(麦克风) |

**成功响应：**

```json
{
  "code": 0,
  "msg": "上传成功",
  "data": { "id": 33, "file_path": "uploads/2026/order_1001_done.jpg", "file_type": "photo" }
}
```

> **非结构化存储要点**：文件本体写入服务器磁盘 `uploads/` 目录，数据库 `delivery_photos` 表只存这条元数据 + 路径。

---

## 五、Web 管理端模块

### 5.1 多维销量分析（分析师）

```
GET /analytics/sales
```
**权限：** analyst

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| dimension | string | 是 | 分析维度：`time`(时段) / `region`(地区) / `category`(品类) |
| start_date | string | 否 | 起始日期，如 `2026-06-01` |
| end_date | string | 否 | 结束日期 |

**成功响应（示例：按品类）：**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "dimension": "category",
    "labels": ["正餐", "饮品", "小吃"],
    "values": [320, 210, 150]
  }
}
```

> 前端拿 `labels` + `values` 直接喂给 ECharts 画柱状图/饼图/折线图。

---

### 5.2 危险路段：列表（监管 / 骑手读）

```
GET /risk-zones
```

**成功响应：**

```json
{
  "code": 0, "msg": "success",
  "data": [
    { "id": 1, "name": "XX 路急转弯", "center_lat": 31.230, "center_lng": 121.474, "radius_m": 150, "risk_level": 3, "description": "夜间照明差" }
  ]
}
```

### 5.3 危险路段：新增（监管维护）

```
POST /risk-zones
```
**权限：** regulator

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | 路段名称 |
| center_lat | number | 是 | 中心纬度 |
| center_lng | number | 是 | 中心经度 |
| radius_m | int | 否 | 影响半径（米），默认 100 |
| risk_level | int | 否 | 风险等级 1-3，默认 1 |
| description | string | 否 | 风险说明 |

**成功响应：** `{ "code": 0, "msg": "已添加", "data": { "id": 2 } }`

---

## 六、AI 模块

### 6.1 菜品推荐

```
GET /ai/recommend
```
**权限：** customer

**成功响应：**

```json
{
  "code": 0, "msg": "success",
  "data": {
    "algorithm": "collaborative",
    "items": [
      { "id": 3, "name": "黄焖鸡米饭", "reason": "和你常点的菜常被一起购买" }
    ]
  }
}
```

> `reason` 字段提供"可解释性"，答辩时演示用。后端同时往 `recommendation_log` 写一条记录。

### 6.2 销量预测

```
GET /ai/forecast
```
**权限：** analyst

**查询参数：** `days`（预测未来几天，默认 7）

**成功响应：**

```json
{
  "code": 0, "msg": "success",
  "data": {
    "history": [ { "date": "2026-06-01", "sales": 120 } ],
    "forecast": [ { "date": "2026-06-09", "sales": 135 } ]
  }
}
```

> 前端把 history + forecast 拼成一条折线，用不同颜色区分"历史"和"预测"。

---

## 七、错误码表

| code | 含义 | 常见 HTTP 状态码 |
| --- | --- | --- |
| 0 | 成功 | 200 |
| 1001 | 用户名已存在 | 200 |
| 1002 | 用户名或密码错误 | 401 |
| 1003 | 验证码错误或过期 | 200 |
| 1004 | 未登录或 token 失效 | 401 |
| 1005 | 无权限访问该接口 | 403 |
| 2001 | 订单已被接单 | 200 |
| 2002 | 订单状态非法流转 | 200 |
| 2003 | 订单不存在 | 404 |
| 3001 | 文件上传失败 | 200 |
| 5000 | 服务器内部错误 | 500 |

> 团队可按需扩充，但**新增错误码必须登记到本表**，避免各写各的。

---

## 八、接口速查表

| 模块 | 方法 | 路径 | 权限 |
| --- | --- | --- | --- |
| 注册 | POST | /auth/register | 公开 |
| 登录 | POST | /auth/login | 公开 |
| 两步验证 | POST | /auth/2fa/verify | 公开 |
| 密码找回 | POST | /auth/recover | 公开 |
| 微信登录 | POST | /auth/wechat | 公开 |
| 菜单列表 | GET | /menu | 登录 |
| 下单 | POST | /orders | customer |
| 订单列表 | GET | /orders | 登录 |
| 订单详情 | GET | /orders/{id} | 登录 |
| 骑手接单 | PUT | /orders/{id}/accept | rider |
| 更新状态 | PUT | /orders/{id}/status | merchant/rider |
| 上传文件 | POST | /upload | 登录 |
| 销量分析 | GET | /analytics/sales | analyst |
| 危险路段列表 | GET | /risk-zones | 登录 |
| 新增危险路段 | POST | /risk-zones | regulator |
| 菜品推荐 | GET | /ai/recommend | customer |
| 销量预测 | GET | /ai/forecast | analyst |

---

## 九、下一步

1. **冻结本契约**：团队过一遍，确认无误后视为"已冻结"。后续如需改接口，必须通知所有人并更新本文件。
2. **导入 Apifox**：把本文件的接口录入 Apifox，开启 Mock，让前端先拿假数据开发（导入方法见团队说明）。
3. **进入 Phase 1**：照 `data_dictionary.md` 在 DB Browser/MySQL 建库；后端照本契约逐个实现接口。
