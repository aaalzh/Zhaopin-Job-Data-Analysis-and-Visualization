"""创建 Spark 统计分析结果表。

连接参数直接配置在本文件顶部。
"""

import pymysql


MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = ""
MYSQL_DATABASE = "shixun"


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `tongji_fenxi_jieguo` (
    `zizeng_bianhao` BIGINT NOT NULL AUTO_INCREMENT,
    `caiji_fanwei_biaoshi` CHAR(64) NOT NULL,
    `guanjianci` VARCHAR(100) DEFAULT NULL,
    `tongji_leixing` VARCHAR(100) NOT NULL,
    `jieguo_json` LONGTEXT NOT NULL,
    `gengxin_shijian` DATETIME NOT NULL,
    PRIMARY KEY (`zizeng_bianhao`),
    UNIQUE KEY `weiyi_fanwei_tongji`
        (`caiji_fanwei_biaoshi`, `tongji_leixing`),
    KEY `suoyin_tongji_leixing` (`tongji_leixing`)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Spark统计分析结果'
"""


def main():
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=False,
        connect_timeout=5,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
        connection.commit()
        print(f"统计分析结果表已就绪: {MYSQL_DATABASE}.tongji_fenxi_jieguo")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
