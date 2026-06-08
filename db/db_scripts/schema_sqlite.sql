-- =============================================================
-- schema_sqlite.sql — 外卖配送信息系统 · SQLite 建表脚本
-- 用法：在 DB Browser for SQLite 里，菜单「执行 SQL」标签整段粘贴执行。
-- 这是原型版，用于快速验证字段设计；正式库请用 schema_mysql.sql。
-- =============================================================

-- 打开外键约束（SQLite 默认关闭，必须每次连接时开启）
PRAGMA foreign_keys = ON;

-- 可重复执行：先删旧表
DROP TABLE IF EXISTS recommendation_log;
DROP TABLE IF EXISTS delivery_photos;
DROP TABLE IF EXISTS order_status_log;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS menu_items;
DROP TABLE IF EXISTS risk_zones;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

-- 角色表
CREATE TABLE roles (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  description  TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 权限表
CREATE TABLE permissions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  code        TEXT NOT NULL UNIQUE,
  description TEXT
);

-- 角色-权限关联表
CREATE TABLE role_permissions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  role_id       INTEGER NOT NULL,
  permission_id INTEGER NOT NULL,
  UNIQUE (role_id, permission_id),
  FOREIGN KEY (role_id)       REFERENCES roles(id),
  FOREIGN KEY (permission_id) REFERENCES permissions(id)
);

-- 用户表
CREATE TABLE users (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  username           TEXT NOT NULL UNIQUE,
  password_hash      TEXT NOT NULL,
  role_id            INTEGER NOT NULL,
  phone              TEXT UNIQUE,
  email              TEXT UNIQUE,
  nickname           TEXT,
  avatar_path        TEXT,
  wechat_openid      TEXT UNIQUE,
  two_factor_enabled INTEGER NOT NULL DEFAULT 0,
  status             INTEGER NOT NULL DEFAULT 1,
  created_at         TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- 菜品表
CREATE TABLE menu_items (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  merchant_id INTEGER NOT NULL,
  name        TEXT NOT NULL,
  price       REAL NOT NULL,
  category    TEXT,
  image_path  TEXT,
  status      INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (merchant_id) REFERENCES users(id)
);

-- 订单表
CREATE TABLE orders (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id      INTEGER NOT NULL,
  rider_id         INTEGER,
  merchant_id      INTEGER NOT NULL,
  total_amount     REAL NOT NULL,
  status           TEXT NOT NULL DEFAULT 'pending',
  delivery_address TEXT NOT NULL,
  dest_lat         REAL,
  dest_lng         REAL,
  remark           TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  completed_at     TEXT,
  FOREIGN KEY (customer_id) REFERENCES users(id),
  FOREIGN KEY (rider_id)    REFERENCES users(id),
  FOREIGN KEY (merchant_id) REFERENCES users(id)
);

-- 订单明细表
CREATE TABLE order_items (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id     INTEGER NOT NULL,
  menu_item_id INTEGER NOT NULL,
  quantity     INTEGER NOT NULL DEFAULT 1,
  unit_price   REAL NOT NULL,
  FOREIGN KEY (order_id)     REFERENCES orders(id),
  FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
);

-- 订单状态流水表
CREATE TABLE order_status_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id    INTEGER NOT NULL,
  status      TEXT NOT NULL,
  operator_id INTEGER,
  changed_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (order_id)    REFERENCES orders(id),
  FOREIGN KEY (operator_id) REFERENCES users(id)
);

-- 配送文件元数据表
CREATE TABLE delivery_photos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id    INTEGER NOT NULL,
  file_path   TEXT NOT NULL,
  file_type   TEXT NOT NULL,
  uploaded_by INTEGER NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (order_id)    REFERENCES orders(id),
  FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

-- 推荐记录表
CREATE TABLE recommendation_log (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id           INTEGER NOT NULL,
  recommended_items TEXT NOT NULL,
  algorithm         TEXT NOT NULL,
  created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 危险路段表
CREATE TABLE risk_zones (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  center_lat  REAL NOT NULL,
  center_lng  REAL NOT NULL,
  radius_m    INTEGER NOT NULL DEFAULT 100,
  risk_level  INTEGER NOT NULL DEFAULT 1,
  description TEXT,
  created_by  INTEGER,
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (created_by) REFERENCES users(id)
);
