-- =============================================================
-- schema_mysql.sql — 外卖配送信息系统 · MySQL 建表脚本
-- 用法：在 MySQL 客户端(Workbench/DBeaver)里整段执行。
-- 字段定义严格对应 docs/data_dictionary.md。
-- =============================================================

-- 1. 创建数据库（utf8mb4 支持中文和 emoji）
CREATE DATABASE IF NOT EXISTS fooddelivery
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE fooddelivery;

-- 为了可重复执行：先按依赖反序删旧表（有外键的先删）
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

-- =============================================================
-- RBAC 权限相关表
-- =============================================================

-- 角色表
CREATE TABLE roles (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  name         VARCHAR(20)  NOT NULL UNIQUE COMMENT '角色英文标识',
  display_name VARCHAR(20)  NOT NULL        COMMENT '中文名',
  description  VARCHAR(100)                 COMMENT '角色说明',
  created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='用户角色表';

-- 权限表
CREATE TABLE permissions (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  code        VARCHAR(50)  NOT NULL UNIQUE COMMENT '权限码',
  description VARCHAR(100)                 COMMENT '权限说明'
) COMMENT='权限项表';

-- 角色-权限关联表（多对多）
CREATE TABLE role_permissions (
  id            INT PRIMARY KEY AUTO_INCREMENT,
  role_id       INT NOT NULL,
  permission_id INT NOT NULL,
  UNIQUE KEY uq_role_perm (role_id, permission_id),
  FOREIGN KEY (role_id)       REFERENCES roles(id),
  FOREIGN KEY (permission_id) REFERENCES permissions(id)
) COMMENT='角色权限关联表';

-- =============================================================
-- 用户表
-- =============================================================
CREATE TABLE users (
  id                 INT PRIMARY KEY AUTO_INCREMENT,
  username           VARCHAR(50)  NOT NULL UNIQUE,
  password_hash      VARCHAR(255) NOT NULL          COMMENT 'bcrypt 哈希，绝不明文',
  role_id            INT          NOT NULL,
  phone              VARCHAR(20)  UNIQUE,
  email              VARCHAR(100) UNIQUE,
  nickname           VARCHAR(50),
  avatar_path        VARCHAR(255),
  wechat_openid      VARCHAR(64)  UNIQUE            COMMENT '微信登录标识',
  two_factor_enabled TINYINT      NOT NULL DEFAULT 0 COMMENT '0 否 1 是',
  status             TINYINT      NOT NULL DEFAULT 1 COMMENT '1 正常 0 禁用',
  created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (role_id) REFERENCES roles(id)
) COMMENT='用户表';

-- =============================================================
-- 核心业务表
-- =============================================================

-- 菜品表
CREATE TABLE menu_items (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  merchant_id INT            NOT NULL COMMENT '所属商家(users.id)',
  name        VARCHAR(100)   NOT NULL,
  price       DECIMAL(10,2)  NOT NULL,
  category    VARCHAR(50)             COMMENT '品类',
  image_path  VARCHAR(255),
  status      TINYINT        NOT NULL DEFAULT 1 COMMENT '1 在售 0 下架',
  created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (merchant_id) REFERENCES users(id)
) COMMENT='菜品表';

-- 订单表
CREATE TABLE orders (
  id               INT PRIMARY KEY AUTO_INCREMENT,
  customer_id      INT            NOT NULL,
  rider_id         INT                     COMMENT '接单骑手，接单前为空',
  merchant_id      INT            NOT NULL,
  total_amount     DECIMAL(10,2)  NOT NULL,
  status           VARCHAR(20)    NOT NULL DEFAULT 'pending',
  delivery_address VARCHAR(255)   NOT NULL,
  dest_lat         DECIMAL(10,7)           COMMENT '目的地纬度 GPS',
  dest_lng         DECIMAL(10,7)           COMMENT '目的地经度 GPS',
  remark           VARCHAR(255),
  created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at     DATETIME                COMMENT '完成时间',
  FOREIGN KEY (customer_id) REFERENCES users(id),
  FOREIGN KEY (rider_id)    REFERENCES users(id),
  FOREIGN KEY (merchant_id) REFERENCES users(id),
  INDEX idx_orders_status (status),
  INDEX idx_orders_created (created_at)
) COMMENT='订单表';

-- 订单明细表
CREATE TABLE order_items (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  order_id     INT           NOT NULL,
  menu_item_id INT           NOT NULL,
  quantity     INT           NOT NULL DEFAULT 1,
  unit_price   DECIMAL(10,2) NOT NULL COMMENT '下单时单价快照',
  FOREIGN KEY (order_id)     REFERENCES orders(id),
  FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
) COMMENT='订单明细表';

-- 订单状态流水表
CREATE TABLE order_status_log (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  order_id    INT         NOT NULL,
  status      VARCHAR(20) NOT NULL COMMENT '变更后的状态',
  operator_id INT                  COMMENT '操作人',
  changed_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id)    REFERENCES orders(id),
  FOREIGN KEY (operator_id) REFERENCES users(id)
) COMMENT='订单状态流水表';

-- =============================================================
-- 硬件与非结构化存储
-- =============================================================

-- 配送文件元数据表（文件本体存磁盘，这里只存路径）
CREATE TABLE delivery_photos (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  order_id    INT          NOT NULL,
  file_path   VARCHAR(255) NOT NULL COMMENT '磁盘相对路径',
  file_type   VARCHAR(10)  NOT NULL COMMENT 'photo 相机 / audio 麦克风',
  uploaded_by INT          NOT NULL COMMENT '上传者(通常骑手)',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id)    REFERENCES orders(id),
  FOREIGN KEY (uploaded_by) REFERENCES users(id)
) COMMENT='配送文件元数据表(非结构化存储)';

-- =============================================================
-- AI 相关表
-- =============================================================
CREATE TABLE recommendation_log (
  id                INT PRIMARY KEY AUTO_INCREMENT,
  user_id           INT         NOT NULL,
  recommended_items TEXT        NOT NULL COMMENT '推荐菜品ID列表(JSON字符串)',
  algorithm         VARCHAR(30) NOT NULL COMMENT 'collaborative / apriori',
  created_at        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
) COMMENT='推荐记录表';

-- =============================================================
-- 伦理功能表（交通-危险路段）
-- =============================================================
CREATE TABLE risk_zones (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(100)  NOT NULL,
  center_lat  DECIMAL(10,7) NOT NULL COMMENT '中心点纬度',
  center_lng  DECIMAL(10,7) NOT NULL COMMENT '中心点经度',
  radius_m    INT           NOT NULL DEFAULT 100 COMMENT '影响半径(米)',
  risk_level  TINYINT       NOT NULL DEFAULT 1   COMMENT '1 低 2 中 3 高',
  description VARCHAR(255),
  created_by  INT                    COMMENT '创建的监管人员',
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id)
) COMMENT='危险路段表(伦理-交通)';

-- 完成。下一步执行 seed.sql 插入演示数据，再执行 rbac.sql 建分级账号。
