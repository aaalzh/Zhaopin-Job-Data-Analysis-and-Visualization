"""
清空项目 MySQL 表数据。

运行方式：
    python sql/03_clear_mysql_data.py

说明：
    本脚本只清空数据，不删除表结构。
"""

import os

import pymysql


MYSQL_HOST = "127.0.0.1"  # MySQL 服务地址
MYSQL_PORT = 3306  # MySQL 服务端口
MYSQL_USER = "root"  # MySQL 登录用户名
MYSQL_PASSWORD = os.environ.get("SHIXUN_MYSQL_PASSWORD", "1472580369@Lzh")  # 优先读取环境变量中的密码
MYSQL_DATABASE = os.environ.get("SHIXUN_MYSQL_DATABASE", "shixun")  # 项目数据库名

TABLES = [
    "raw_job_info",
    "raw_company_info",
    "raw_hr_status_info",
    "crawler_log",
    "clean_job_detail",
    "clean_company_info",
    "clean_hr_status_info",
    "clean_log",
]


def get_mysql_connection():
    """
    Input:
    - 无。
    Output:
    - pymysql.Connection，连接到项目数据库的 MySQL 连接。
    Function:
    - 连接项目数据库，用于执行清空数据语句。
    """
    return pymysql.connect(
        host=MYSQL_HOST,
        port=int(MYSQL_PORT),
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=True,
    )


def clear_mysql_data():
    """
    Input:
    - 无。
    Output:
    - None。
    Function:
    - 使用 TRUNCATE 清空项目 8 张表的数据，并保留表结构。
    """
    with get_mysql_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in TABLES:
                cursor.execute(f"TRUNCATE TABLE `{table}`")
                print(f"已清空: {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("MySQL 项目表数据已清空。")


if __name__ == "__main__":
    clear_mysql_data()
