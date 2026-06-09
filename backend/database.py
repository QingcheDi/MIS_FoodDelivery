"""
database.py — 数据库连接配置

启动时自动加载同目录下的 .env 文件读取数据库密码等敏感信息。
.env 已被 .gitignore 排除，不会上传到 GitHub，因此本文件里不出现任何真实密码。
队友拿到代码后，照 .env.example 自建一份 .env 即可。
"""
import os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

# 自动加载同目录下的 .env 文件（把里面的变量注入到环境变量）
load_dotenv()

# ---- 数据库连接参数（全部从环境变量读取）----
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),  # 真实密码在 .env 里，绝不写死在代码中
    "database": os.getenv("DB_NAME", "fooddelivery"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,  # 查询结果以字典形式返回，便于转 JSON
}


def get_connection():
    """获取一个新的数据库连接。用完记得 close()。"""
    return pymysql.connect(**DB_CONFIG)
