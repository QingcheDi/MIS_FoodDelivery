# db/ 脚本执行说明

四份脚本，按下面顺序使用。

## 路线一：先用 DB Browser (SQLite) 跑原型（推荐先做）

1. 打开 DB Browser for SQLite → 「新建数据库」，存为 `prototype.sqlite`。
2. 顶部「执行 SQL」标签 → 粘贴 `schema_sqlite.sql` 全部内容 → 点执行（▶）。
3. 再粘贴 `seed.sql` 全部内容 → 执行。
4. 切到「浏览数据」标签，能看到 11 张表和演示数据，原型验证完成。

> 注意：SQLite 每次要先执行 `PRAGMA foreign_keys = ON;`（schema 脚本已含）。

## 路线二：正式库 MySQL

1. 打开 MySQL Workbench 或 DBeaver，连上本地 MySQL。
2. 执行 `schema_mysql.sql`（会自动建库 fooddelivery + 11 张表）。
3. 执行 `seed.sql`（灌演示数据；执行前确保已 `USE fooddelivery;`）。
4. 用 root 执行 `rbac.sql`（建分级权限账号，数据库层 RBAC 评分点）。

## 演示账号

所有用户密码都是 **123456**：
- 顾客：customer01 / customer02 / customer03
- 骑手：rider01 / rider02
- 商家：merchant01 / merchant02
- 分析师：analyst01
- 监管：regulator01

数据库分级账号（rbac.sql 创建）：
- analyst / Analyst@123（全库只读）
- regulator / Regulator@123（只读视图 + 维护危险路段）
