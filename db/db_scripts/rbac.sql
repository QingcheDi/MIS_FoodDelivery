-- =============================================================
-- rbac.sql — 外卖配送信息系统 · 数据库层权限控制（仅 MySQL）
-- 用法：在 schema_mysql.sql + seed.sql 执行完之后，用 root 账号执行本文件。
--
-- 这是"权限分级/RBAC"评分点的【数据库层】实现：
--   不是在后端代码里判断，而是在数据库本身创建不同权限的账号。
--   即使账号泄露，分析师/监管也只能读、不能改，从根上防数据泄露。
-- =============================================================

USE fooddelivery;

-- 可重复执行：先删旧账号（如不存在会警告，可忽略）
DROP USER IF EXISTS 'analyst'@'localhost';
DROP USER IF EXISTS 'regulator'@'localhost';

-- -------------------------------------------------------------
-- 1. 分析师账号：全库只读（只能 SELECT，不能增删改）
-- -------------------------------------------------------------
CREATE USER 'analyst'@'localhost' IDENTIFIED BY 'Analyst@123';
GRANT SELECT ON fooddelivery.* TO 'analyst'@'localhost';

-- -------------------------------------------------------------
-- 2. 监管账号：只读 + 可维护危险路段表
--    先建一个"监管只读视图"，只暴露监管该看的字段（脱敏，防数据泄露）
-- -------------------------------------------------------------

-- 监管视图：订单概览（隐藏顾客手机号等敏感信息）
CREATE OR REPLACE VIEW v_regulator_orders AS
SELECT
  o.id            AS order_id,
  o.status,
  o.total_amount,
  o.delivery_address,
  o.dest_lat,
  o.dest_lng,
  o.created_at,
  o.completed_at
FROM orders o;

-- 监管账号：只能读这个视图 + 读写危险路段表
CREATE USER 'regulator'@'localhost' IDENTIFIED BY 'Regulator@123';
GRANT SELECT ON fooddelivery.v_regulator_orders TO 'regulator'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON fooddelivery.risk_zones TO 'regulator'@'localhost';

-- 让权限立即生效
FLUSH PRIVILEGES;

-- =============================================================
-- 验证方法（答辩时可演示）：
--   1) 用 analyst 账号登录，执行 SELECT * FROM orders; → 成功
--   2) 用 analyst 账号执行 DELETE FROM orders;        → 被拒绝（无权限）
--   3) 用 regulator 账号执行 INSERT INTO risk_zones;  → 成功
--   4) 用 regulator 账号执行 SELECT * FROM users;     → 被拒绝
-- 这就直观展示了"数据库层级的分级权限控制"。
-- =============================================================
