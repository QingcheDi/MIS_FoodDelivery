# 数据字典 — 外卖配送信息系统

> 本文件定义数据库中**每一张表、每一个字段**的含义、类型与约束。它是 `db/` 建表脚本和 `backend/` 数据模型的共同蓝图——所有人照此实现，保证前后端、数据库三方一致。
>
> **设计基线**：5 种角色完整 RBAC；核心下单/接单/完成流程；硬件采集（GPS/相机/麦克风）；非结构化存储（文件存磁盘、库存路径）；AI 推荐与销量预测；交通-危险路段伦理功能；两步验证与微信登录。

---

## 一、阅读约定

- **类型**：用 MySQL 类型。`INT` 整数；`BIGINT` 大整数；`VARCHAR(n)` 变长字符串；`DECIMAL(10,2)` 金额（10 位含 2 位小数）；`DATETIME` 日期时间；`TEXT` 长文本；`TINYINT` 小整数（常用作布尔，0/1）。
- **PK** = 主键（Primary Key，每行的唯一标识）；**FK** = 外键（Foreign Key，指向另一张表的主键）。
- **可空**：`NOT NULL` 表示该字段必填；可空表示允许为空。
- 所有表统一用 `id` 作自增主键，统一带 `created_at` 创建时间。
- 字符集统一 `utf8mb4`（支持 emoji 和全部中文）。

---

## 二、表关系总览（ER 概念图）

```
roles ──< users ──< orders >── menu_items
  │                   │
  └──< role_permissions      ├──< order_status_log
        │                    └──< delivery_photos
  permissions ──┘
                       recommendation_log >── users
                       risk_zones (独立维护表)
```

含义：一个角色(roles)对应多个用户(users)；一个用户可下多个订单(orders)；一个订单含多条状态流水(order_status_log)和多个配送文件(delivery_photos)；角色与权限通过中间表(role_permissions)多对多关联。

---

## 三、权限相关表（RBAC）

### 3.1 `roles` — 角色表

存放系统的 5 种用户角色。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 角色 ID |
| name | VARCHAR(20) | NOT NULL, UNIQUE | 角色英文标识：customer/rider/merchant/analyst/regulator |
| display_name | VARCHAR(20) | NOT NULL | 中文名：顾客/骑手/商家/分析师/监管 |
| description | VARCHAR(100) | 可空 | 角色说明 |
| created_at | DATETIME | NOT NULL, 默认当前时间 | 创建时间 |

**初始数据**：customer(顾客)、rider(骑手)、merchant(商家)、analyst(分析师)、regulator(监管)。

### 3.2 `permissions` — 权限表

存放可分配的权限项（一个个原子操作）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 权限 ID |
| code | VARCHAR(50) | NOT NULL, UNIQUE | 权限码，如 `order.create`、`order.accept`、`analytics.view` |
| description | VARCHAR(100) | 可空 | 权限说明 |

**示例权限**：`order.create`(下单)、`order.accept`(接单)、`order.update_status`(改状态)、`menu.manage`(管理菜单)、`analytics.view`(看分析)、`regulator.view`(监管只读)、`riskzone.manage`(维护危险路段)。

### 3.3 `role_permissions` — 角色权限关联表

把角色和权限多对多关联起来（哪个角色拥有哪些权限）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 关联 ID |
| role_id | INT | FK → roles.id, NOT NULL | 角色 |
| permission_id | INT | FK → permissions.id, NOT NULL | 权限 |

> 唯一约束：(role_id, permission_id) 组合不重复。

---

## 四、用户表

### 4.1 `users` — 用户表

所有角色的用户都存这张表，靠 `role_id` 区分身份。**密码只存 bcrypt 哈希，绝不存明文。** 两步验证、微信登录的相关字段也在此。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 用户 ID |
| username | VARCHAR(50) | NOT NULL, UNIQUE | 登录用户名 |
| password_hash | VARCHAR(255) | NOT NULL | **bcrypt 加密后**的密码哈希，绝不明文 |
| role_id | INT | FK → roles.id, NOT NULL | 所属角色 |
| phone | VARCHAR(20) | 可空, UNIQUE | 手机号（用于短信验证码 / 找回密码） |
| email | VARCHAR(100) | 可空, UNIQUE | 邮箱（用于邮件找回密码） |
| nickname | VARCHAR(50) | 可空 | 昵称 |
| avatar_path | VARCHAR(255) | 可空 | 头像文件路径 |
| wechat_openid | VARCHAR(64) | 可空, UNIQUE | 微信登录标识（微信 OAuth 用，可 mock） |
| two_factor_enabled | TINYINT | NOT NULL, 默认 0 | 是否启用两步验证：0 否 1 是 |
| status | TINYINT | NOT NULL, 默认 1 | 账号状态：1 正常 0 禁用 |
| created_at | DATETIME | NOT NULL, 默认当前时间 | 注册时间 |

> **安全/脱敏提示**：接口返回用户信息时，`password_hash`、`wechat_openid` 等字段绝不返回；`phone`、`email` 视情况脱敏（如 `138****5678`），体现"防数据泄露"。

---

## 五、核心业务表

### 5.1 `menu_items` — 菜品表

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 菜品 ID |
| merchant_id | INT | FK → users.id, NOT NULL | 所属商家（users 表中 role=merchant 的用户） |
| name | VARCHAR(100) | NOT NULL | 菜品名称 |
| price | DECIMAL(10,2) | NOT NULL | 单价 |
| category | VARCHAR(50) | 可空 | 品类（用于分析师按品类分析） |
| image_path | VARCHAR(255) | 可空 | 菜品图片路径 |
| status | TINYINT | NOT NULL, 默认 1 | 上架状态：1 在售 0 下架 |
| created_at | DATETIME | NOT NULL, 默认当前时间 | 创建时间 |

### 5.2 `orders` — 订单表

整个系统的核心表，串联顾客、骑手、商家。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 订单 ID |
| customer_id | INT | FK → users.id, NOT NULL | 下单顾客 |
| rider_id | INT | FK → users.id, 可空 | 接单骑手（接单前为空） |
| merchant_id | INT | FK → users.id, NOT NULL | 出餐商家 |
| total_amount | DECIMAL(10,2) | NOT NULL | 订单总金额 |
| status | VARCHAR(20) | NOT NULL, 默认 'pending' | 订单状态（见下方枚举） |
| delivery_address | VARCHAR(255) | NOT NULL | 配送地址 |
| dest_lat | DECIMAL(10,7) | 可空 | 目的地纬度（GPS） |
| dest_lng | DECIMAL(10,7) | 可空 | 目的地经度（GPS） |
| remark | VARCHAR(255) | 可空 | 备注（如语音搜索转写的需求） |
| created_at | DATETIME | NOT NULL, 默认当前时间 | 下单时间 |
| completed_at | DATETIME | 可空 | 完成时间（用于时段分析） |

**status 枚举值**（订单状态流转）：
`pending`(待接单) → `accepted`(商家已接) → `preparing`(出餐中) → `delivering`(配送中) → `completed`(已完成)；另有 `cancelled`(已取消)。

### 5.3 `order_items` — 订单明细表

一个订单可含多个菜品，明细单独存（避免在 orders 表里塞数组）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 明细 ID |
| order_id | INT | FK → orders.id, NOT NULL | 所属订单 |
| menu_item_id | INT | FK → menu_items.id, NOT NULL | 菜品 |
| quantity | INT | NOT NULL, 默认 1 | 数量 |
| unit_price | DECIMAL(10,2) | NOT NULL | 下单时单价（快照，防菜品改价后历史错乱） |

### 5.4 `order_status_log` — 订单状态流水表

每次订单状态变化记一行，可完整追溯（答辩时演示"订单生命周期"很有用）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 流水 ID |
| order_id | INT | FK → orders.id, NOT NULL | 所属订单 |
| status | VARCHAR(20) | NOT NULL | 变更后的状态 |
| operator_id | INT | FK → users.id, 可空 | 操作人 |
| changed_at | DATETIME | NOT NULL, 默认当前时间 | 变更时间 |

---

## 六、硬件与非结构化存储

### 6.1 `delivery_photos` — 配送文件元数据表

**这是"非结构化存储"评分点的核心。** 真实文件（照片/语音）存在服务器磁盘 `uploads/` 目录，**数据库只存一行元数据 + 路径**，不存文件本体。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 记录 ID |
| order_id | INT | FK → orders.id, NOT NULL | 关联订单 |
| file_path | VARCHAR(255) | NOT NULL | 文件在磁盘的相对路径，如 `uploads/2026/order_12_done.jpg` |
| file_type | VARCHAR(10) | NOT NULL | 类型：`photo`(相机拍照) / `audio`(麦克风语音) |
| uploaded_by | INT | FK → users.id, NOT NULL | 上传者（通常是骑手） |
| created_at | DATETIME | NOT NULL, 默认当前时间 | 上传时间 |

> **硬件对应关系**：相机 → 骑手送达拍照存为 `photo`；麦克风 → 顾客语音搜索存为 `audio`；GPS → 经纬度存在 orders 表的 dest_lat/dest_lng 和（如需）骑手实时位置。

---

## 七、AI 相关表

AI 的推荐和预测主要**基于 orders / order_items 的历史数据计算**，本身不一定需要新表。但建一张日志表记录推荐结果，便于答辩演示"可解释性"。

### 7.1 `recommendation_log` — 推荐记录表

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 记录 ID |
| user_id | INT | FK → users.id, NOT NULL | 被推荐的顾客 |
| recommended_items | TEXT | NOT NULL | 推荐的菜品 ID 列表（JSON 字符串，如 `[3,7,12]`） |
| algorithm | VARCHAR(30) | NOT NULL | 算法名：`collaborative`(协同过滤) / `apriori`(关联规则) |
| created_at | DATETIME | NOT NULL, 默认当前时间 | 生成时间 |

> 销量预测（时间序列）直接对 orders 按时间聚合计算即可，结果用 ECharts 出趋势图，**无需单独建表**。

---

## 八、伦理功能表（交通-危险路段）

### 8.1 `risk_zones` — 危险路段表

监管角色维护，用于给骑手做安全路线提示（体现"伦理-交通"评分点）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT | PK, AUTO_INCREMENT | 路段 ID |
| name | VARCHAR(100) | NOT NULL | 路段名称，如"XX 路急转弯" |
| center_lat | DECIMAL(10,7) | NOT NULL | 中心点纬度 |
| center_lng | DECIMAL(10,7) | NOT NULL | 中心点经度 |
| radius_m | INT | NOT NULL, 默认 100 | 影响半径（米） |
| risk_level | TINYINT | NOT NULL, 默认 1 | 风险等级：1 低 2 中 3 高 |
| description | VARCHAR(255) | 可空 | 风险说明（如"夜间照明差""事故高发"） |
| created_by | INT | FK → users.id, 可空 | 创建的监管人员 |
| created_at | DATETIME | NOT NULL, 默认当前时间 | 创建时间 |

> **业务逻辑**：骑手 GPS 位置（orders 的 dest_lat/lng 或实时定位）若落在某 risk_zone 半径内，前端给出安全提示。这就是"risk_zones 驱动的安全路线判断"。

---

## 九、表清单速查

| 表名 | 作用 | 对应评分点 |
| --- | --- | --- |
| roles | 5 种角色 | 多角色 / 权限分级 |
| permissions | 权限项 | 权限分级 RBAC |
| role_permissions | 角色-权限关联 | 权限分级 RBAC |
| users | 用户 | 登录 / 密码加密 / 两步验证 / 微信登录 |
| menu_items | 菜品 | 下单流程 / 品类分析 |
| orders | 订单 | 核心流程 / GPS / 时段分析 |
| order_items | 订单明细 | 下单流程 |
| order_status_log | 状态流水 | 接单/完成 可追溯 |
| delivery_photos | 配送文件元数据 | 非结构化存储 / 相机 / 麦克风 |
| recommendation_log | 推荐记录 | AI 推荐 |
| risk_zones | 危险路段 | 伦理-交通 |

---

## 十、下一步

数据字典定稿后，进入 **Phase 1**：

1. 在 DB Browser for SQLite 里按本字典快速搭原型、验证字段。
2. 写成 `db/schema.sql`（CREATE TABLE 语句），在 MySQL 建正式库。
3. 写 `db/rbac.sql`：给 analyst 建只读账号、给 regulator 建只读视图账号（数据库层 RBAC）。
4. 写 `db/seed.sql`：插入演示用的假数据。

> 在那之前，建议先和 **API 契约文档** 配套定稿——字段（本文件）+ 接口（API 契约）两份齐全，前后端就能并行开工，Phase 0 正式收尾。
