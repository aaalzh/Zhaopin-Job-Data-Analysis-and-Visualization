"""
创建项目 MySQL 数据表。

运行方式：
    python sql/02_create_mysql_tables.py

说明：
    本脚本只负责建表，不清空已有数据。
    表已存在时会跳过，不会自动迁移旧表结构。
"""

import os

import pymysql


MYSQL_HOST = "127.0.0.1"  # MySQL 服务地址
MYSQL_PORT = 3306  # MySQL 服务端口
MYSQL_USER = "root"  # MySQL 登录用户名
MYSQL_PASSWORD = os.environ.get("SHIXUN_MYSQL_PASSWORD", "1472580369@Lzh")  # 优先读取环境变量中的密码
MYSQL_DATABASE = os.environ.get("SHIXUN_MYSQL_DATABASE", "shixun")  # 项目数据库名


CREATE_TABLE_SQL_LIST = [
    """
    CREATE TABLE IF NOT EXISTS `raw_job_info` (
      `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
      `run_id` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '批次唯一编号',
      `batch_no` int NOT NULL COMMENT '同关键字下的批次序号',
      `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
      `source_city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '搜索城市',
      `city_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '城市代码',
      `page_no` int DEFAULT NULL COMMENT '页码',
      `job_sign` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位签名',
      `is_current` tinyint NOT NULL DEFAULT '0' COMMENT '是否当前批次：1是，0否',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `职位ID` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位ID',
      `职位编号` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位编号',
      `职位名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位名称',
      `职位URL` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位URL',
      `薪资` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '薪资',
      `薪资原始区间` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '薪资原始区间',
      `薪资类型` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '薪资类型',
      `薪资发放次数` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '薪资发放次数',
      `工作城市` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作城市',
      `行政区` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行政区',
      `商圈/街道` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '商圈/街道',
      `工作地点展示` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作地点展示',
      `详细地址` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '详细地址',
      `经度` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '经度',
      `纬度` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '纬度',
      `经验要求` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '经验要求',
      `学历要求` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学历要求',
      `工作类型` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作类型',
      `工作模式` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作模式',
      `职位类别` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位类别',
      `公司名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司名称',
      `发布时间` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发布时间',
      `首次发布时间` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '首次发布时间',
      `发布日期文本` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发布日期文本',
      `是否新职位` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '是否新职位',
      `招聘人数` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '招聘人数',
      `职位标签汇总` text COLLATE utf8mb4_unicode_ci COMMENT '职位标签汇总',
      `搜索命中关键词` text COLLATE utf8mb4_unicode_ci COMMENT '搜索命中关键词',
      `技能标签` text COLLATE utf8mb4_unicode_ci COMMENT '技能标签',
      `福利标签` text COLLATE utf8mb4_unicode_ci COMMENT '福利标签',
      `福利明细` text COLLATE utf8mb4_unicode_ci COMMENT '福利明细',
      `工作时间` text COLLATE utf8mb4_unicode_ci COMMENT '工作时间',
      `报告项/保障项` text COLLATE utf8mb4_unicode_ci COMMENT '报告项/保障项',
      `职位描述` longtext COLLATE utf8mb4_unicode_ci COMMENT '职位描述',
      `职位亮点` longtext COLLATE utf8mb4_unicode_ci COMMENT '职位亮点',
      `职位摘要` longtext COLLATE utf8mb4_unicode_ci COMMENT '职位摘要',
      `认证/守护信息` text COLLATE utf8mb4_unicode_ci COMMENT '认证/守护信息',
      `原始JSON` longtext COLLATE utf8mb4_unicode_ci COMMENT '原始JSON',
      PRIMARY KEY (`id`),
      KEY `idx_raw_job_run` (`run_id`),
      KEY `idx_raw_job_sign` (`job_sign`),
      KEY `idx_raw_job_city` (`source_city`),
      KEY `idx_raw_job_batch` (`keyword`,`batch_no`),
      KEY `idx_raw_job_current` (`keyword`,`is_current`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='原始岗位信息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `raw_company_info` (
      `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
      `run_id` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '批次唯一编号',
      `batch_no` int NOT NULL COMMENT '同关键字下的批次序号',
      `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
      `source_city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '搜索城市',
      `company_sign` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司签名',
      `is_current` tinyint NOT NULL DEFAULT '0' COMMENT '是否当前批次：1是，0否',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `公司名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司名称',
      `公司编号` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司编号',
      `公司URL` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司URL',
      `公司Logo` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司Logo',
      `公司规模` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司规模',
      `公司性质` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司性质',
      `融资阶段` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '融资阶段',
      `行业` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行业',
      PRIMARY KEY (`id`),
      KEY `idx_raw_company_run` (`run_id`),
      KEY `idx_raw_company_name` (`公司名称`),
      KEY `idx_raw_company_city` (`source_city`),
      KEY `idx_raw_company_batch` (`keyword`,`batch_no`),
      KEY `idx_raw_company_current` (`keyword`,`is_current`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='原始公司信息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `raw_hr_status_info` (
      `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
      `run_id` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '批次唯一编号',
      `batch_no` int NOT NULL COMMENT '同关键字下的批次序号',
      `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
      `source_city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '搜索城市',
      `job_sign` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位签名',
      `hr_sign` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR签名',
      `is_current` tinyint NOT NULL DEFAULT '0' COMMENT '是否当前批次：1是，0否',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `职位名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位名称',
      `公司名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司名称',
      `HR姓名` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR姓名',
      `HR职位` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR职位',
      `HR状态` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR状态',
      `HR活跃标签` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR活跃标签',
      PRIMARY KEY (`id`),
      KEY `idx_raw_hr_run` (`run_id`),
      KEY `idx_raw_hr_job_sign` (`job_sign`),
      KEY `idx_raw_hr_status` (`HR状态`),
      KEY `idx_raw_hr_batch` (`keyword`,`batch_no`),
      KEY `idx_raw_hr_current` (`keyword`,`is_current`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='原始HR状态表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `crawler_log` (
      `log_id` bigint NOT NULL AUTO_INCREMENT COMMENT '日志ID',
      `run_id` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '批次唯一编号',
      `batch_no` int NOT NULL COMMENT '同关键字下的批次序号',
      `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
      `source_cities` text COLLATE utf8mb4_unicode_ci COMMENT '本批次抓取城市',
      `planned_city_count` int DEFAULT '0' COMMENT '计划城市数',
      `success_city_count` int DEFAULT '0' COMMENT '成功城市数',
      `failed_city_count` int DEFAULT '0' COMMENT '失败城市数',
      `job_record_count` int DEFAULT '0' COMMENT '岗位记录数',
      `company_record_count` int DEFAULT '0' COMMENT '公司记录数',
      `hr_record_count` int DEFAULT '0' COMMENT 'HR记录数',
      `run_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '运行状态：success/partial/failed',
      `run_message` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '运行说明或错误信息',
      `start_time` datetime DEFAULT NULL COMMENT '开始时间',
      `end_time` datetime DEFAULT NULL COMMENT '结束时间',
      `is_current` tinyint NOT NULL DEFAULT '0' COMMENT '是否当前批次：1是，0否',
      `is_retained` tinyint NOT NULL DEFAULT '1' COMMENT '业务数据是否仍保留：1是，0否',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '日志创建时间',
      `deleted_at` datetime DEFAULT NULL COMMENT '超过5批后业务数据删除时间',
      PRIMARY KEY (`log_id`),
      UNIQUE KEY `uk_crawler_run` (`run_id`),
      KEY `idx_crawler_keyword` (`keyword`),
      KEY `idx_crawler_current` (`keyword`,`is_current`),
      KEY `idx_crawler_batch` (`keyword`,`batch_no`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='爬虫日志表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `clean_job_detail` (
      `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
      `raw_job_id` bigint DEFAULT NULL COMMENT '原始岗位表ID',
      `run_id` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '批次唯一编号',
      `batch_no` int NOT NULL COMMENT '同关键字下的批次序号',
      `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
      `source_city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '搜索城市',
      `job_sign` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位签名',
      `is_current` tinyint NOT NULL DEFAULT '0' COMMENT '是否当前批次：1是，0否',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `职位名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位名称',
      `最低薪资` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '最低薪资',
      `最高薪资` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '最高薪资',
      `工作地点展示` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作地点展示',
      `经验要求` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '经验要求',
      `学历要求` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学历要求',
      `工作类型` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作类型',
      `工作模式` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工作模式',
      `职位类别` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位类别',
      `公司名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司名称',
      `公司规模` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司规模',
      `公司性质` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司性质',
      `融资阶段` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '融资阶段',
      `行业` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行业',
      `发布时间` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发布时间',
      `HR状态` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR状态',
      `HR活跃标签` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR活跃标签',
      `技能标签` text COLLATE utf8mb4_unicode_ci COMMENT '技能标签',
      `职位描述` longtext COLLATE utf8mb4_unicode_ci COMMENT '职位描述',
      PRIMARY KEY (`id`),
      KEY `idx_clean_job_run` (`run_id`),
      KEY `idx_clean_job_sign` (`job_sign`),
      KEY `idx_clean_job_company` (`公司名称`),
      KEY `idx_clean_job_location` (`工作地点展示`),
      KEY `idx_clean_job_category` (`职位类别`),
      KEY `idx_clean_job_batch` (`keyword`,`batch_no`),
      KEY `idx_clean_job_current` (`keyword`,`is_current`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='清洗后岗位明细表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `clean_company_info` (
      `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
      `run_id` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '批次唯一编号',
      `batch_no` int NOT NULL COMMENT '同关键字下的批次序号',
      `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
      `source_city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '搜索城市',
      `company_sign` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司签名',
      `is_current` tinyint NOT NULL DEFAULT '0' COMMENT '是否当前批次：1是，0否',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `公司名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司名称',
      `公司规模` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司规模',
      `公司性质` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司性质',
      `融资阶段` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '融资阶段',
      `行业` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行业',
      PRIMARY KEY (`id`),
      KEY `idx_clean_company_run` (`run_id`),
      KEY `idx_clean_company_name` (`公司名称`),
      KEY `idx_clean_company_city` (`source_city`),
      KEY `idx_clean_company_batch` (`keyword`,`batch_no`),
      KEY `idx_clean_company_current` (`keyword`,`is_current`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='清洗后公司信息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `clean_hr_status_info` (
      `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增ID',
      `run_id` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '批次唯一编号',
      `batch_no` int NOT NULL COMMENT '同关键字下的批次序号',
      `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
      `source_city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '搜索城市',
      `job_sign` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '岗位签名',
      `hr_sign` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR签名',
      `is_current` tinyint NOT NULL DEFAULT '0' COMMENT '是否当前批次：1是，0否',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `职位名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '职位名称',
      `公司名称` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公司名称',
      `HR状态` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR状态',
      `HR活跃标签` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HR活跃标签',
      PRIMARY KEY (`id`),
      KEY `idx_clean_hr_run` (`run_id`),
      KEY `idx_clean_hr_job_sign` (`job_sign`),
      KEY `idx_clean_hr_status` (`HR状态`),
      KEY `idx_clean_hr_batch` (`keyword`,`batch_no`),
      KEY `idx_clean_hr_current` (`keyword`,`is_current`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='清洗后HR状态表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `clean_log` (
      `log_id` bigint NOT NULL AUTO_INCREMENT COMMENT '日志ID',
      `run_id` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '批次唯一编号',
      `batch_no` int NOT NULL COMMENT '同关键字下的批次序号',
      `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
      `source_cities` text COLLATE utf8mb4_unicode_ci COMMENT '本批次清洗城市',
      `job_record_count` int DEFAULT '0' COMMENT '清洗后岗位记录数',
      `company_record_count` int DEFAULT '0' COMMENT '清洗后公司记录数',
      `hr_record_count` int DEFAULT '0' COMMENT '清洗后HR记录数',
      `hdfs_output_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HDFS输出路径',
      `run_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '运行状态：success/failed',
      `run_message` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '运行说明或错误信息',
      `start_time` datetime DEFAULT NULL COMMENT '开始时间',
      `end_time` datetime DEFAULT NULL COMMENT '结束时间',
      `is_current` tinyint NOT NULL DEFAULT '0' COMMENT '是否当前批次：1是，0否',
      `is_retained` tinyint NOT NULL DEFAULT '1' COMMENT '业务数据是否仍保留：1是，0否',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '日志创建时间',
      `deleted_at` datetime DEFAULT NULL COMMENT '超过5批后业务数据删除时间',
      PRIMARY KEY (`log_id`),
      UNIQUE KEY `uk_clean_run` (`run_id`),
      KEY `idx_clean_log_keyword` (`keyword`),
      KEY `idx_clean_log_current` (`keyword`,`is_current`),
      KEY `idx_clean_log_batch` (`keyword`,`batch_no`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='清洗日志表'
    """,
]


def get_mysql_connection():
    """
    Input:
    - 无。
    Output:
    - pymysql.Connection，连接到项目数据库的 MySQL 连接。
    Function:
    - 连接项目数据库，用于执行建表语句。
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


def create_tables():
    """
    Input:
    - 无。
    Output:
    - None。
    Function:
    - 创建项目需要的 8 张 MySQL 表；表已存在时跳过。
    """
    with get_mysql_connection() as connection:
        with connection.cursor() as cursor:
            for create_sql in CREATE_TABLE_SQL_LIST:
                cursor.execute(create_sql)
    print(f"MySQL 表已准备好: {MYSQL_DATABASE}")


if __name__ == "__main__":
    create_tables()
