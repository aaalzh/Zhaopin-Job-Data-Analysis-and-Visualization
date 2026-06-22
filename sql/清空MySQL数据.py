"""
清空项目 MySQL 表数据。

运行方式：
    python sql/清空MySQL数据.py

说明：
    本脚本只清空数据，不删除表结构。
"""

import pymysql


MYSQL_HOST = "127.0.0.1"  # MySQL 服务地址
MYSQL_PORT = 3306  # MySQL 服务端口
MYSQL_USER = "root"  # MySQL 登录用户名
MYSQL_PASSWORD = ""  # MySQL 登录密码
MYSQL_DATABASE = "shixun"  # 项目数据库名

TABLES = [
    "yuan_shi_gangwei_xinxi",
    "yuan_shi_gongsi_xinxi",
    "yuan_shi_zhaopin_fuzeren_xinxi",
    "pachong_yunxing_rizhi",
    "qingxi_gangwei_mingxi",
    "qingxi_gongsi_xinxi",
    "qingxi_zhaopin_fuzeren_xinxi",
    "qingxi_yunxing_rizhi",
    "tongji_fenxi_jieguo",
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
    - 使用 TRUNCATE 清空已存在的项目业务表和统计结果表，并保留表结构。
    """
    with get_mysql_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                for table in TABLES:
                    cursor.execute("SHOW TABLES LIKE %s", (table,))
                    if cursor.fetchone() is None:
                        print(f"已跳过不存在的表: {table}")
                        continue
                    cursor.execute(f"TRUNCATE TABLE `{table}`")
                    print(f"已清空: {table}")
            finally:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("MySQL 项目表数据已清空。")


if __name__ == "__main__":
    clear_mysql_data()
