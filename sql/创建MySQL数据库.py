"""
创建项目 MySQL 数据库。

运行方式：
    python sql/01_create_mysql_database.py
"""

import os

import pymysql


MYSQL_HOST = "127.0.0.1"  # MySQL 服务地址
MYSQL_PORT = 3306  # MySQL 服务端口
MYSQL_USER = "root"  # MySQL 登录用户名
MYSQL_PASSWORD = os.environ.get("SHIXUN_MYSQL_PASSWORD", "1472580369@Lzh")  # 优先读取环境变量中的密码
MYSQL_DATABASE = os.environ.get("SHIXUN_MYSQL_DATABASE", "shixun")  # 项目数据库名


def get_mysql_connection():
    """
    Input:
    - 无。
    Output:
    - pymysql.Connection，不指定数据库的 MySQL 连接。
    Function:
    - 连接 MySQL 服务，用于执行建库语句。
    """
    return pymysql.connect(
        host=MYSQL_HOST,
        port=int(MYSQL_PORT),
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=True,
    )


def create_database():
    """
    Input:
    - 无。
    Output:
    - None。
    Function:
    - 创建项目数据库；如果数据库已经存在，不会删除或覆盖。
    """
    sql = (
        f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
        "DEFAULT CHARACTER SET utf8mb4 "
        "DEFAULT COLLATE utf8mb4_unicode_ci"
    )
    with get_mysql_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
    print(f"数据库已准备好: {MYSQL_DATABASE}")


if __name__ == "__main__":
    create_database()
