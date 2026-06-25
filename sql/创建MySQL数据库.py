"""
创建项目 MySQL 数据库。

运行方式：
    python sql/创建MySQL数据库.py
"""

import pymysql


from db_config import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER


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
