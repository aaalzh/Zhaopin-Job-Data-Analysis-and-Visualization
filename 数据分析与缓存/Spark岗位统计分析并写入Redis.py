#!/usr/bin/env python
# coding: utf-8

# Spark 岗位统计分析并写入 Redis
# 本脚本对 Hive 岗位/技能明细执行独立统计，先把统一 JSON 写入 MySQL，提交成功后再同步到 Redis。
# - 默认数据源为 Hive；只有手动把 `DATA_SOURCE` 改为 `"hdfs"` 才读取 ORC 目录，不会静默切换。
# - MySQL 密码、Redis 密码等涉密值从系统环境变量读取；非涉密默认值在参数配置区。
# - 运行前先执行 `sql/创建MySQL数据表.py`，会同时创建业务表和统计结果表。
# - 依赖：`pyspark`、`pymysql`、`redis`。
# 1. 参数配置：通常只需修改关键词、关键词代码和关键词标识。
import os

DATA_SOURCE = "hive"  # 只能是 "hive" 或 "hdfs"

KEYWORD = "数据开发"
KEYWORD_CODE = "shuju_kaifa"
SCOPE_ID = KEYWORD_CODE

HIVE_DATABASE = "zhaopin_shucang"
HIVE_JOB_TABLE = f"mingxi_gangwei_xinxi_{KEYWORD_CODE}"
HIVE_SKILL_TABLE = f"mingxi_gangwei_jineng_{KEYWORD_CODE}"

HDFS_URI = "hdfs://localhost:9000"
HDFS_JOB_PATH = f"/user/hive/warehouse/{HIVE_DATABASE}.db/{HIVE_JOB_TABLE}"
HDFS_SKILL_PATH = f"/user/hive/warehouse/{HIVE_DATABASE}.db/{HIVE_SKILL_TABLE}"

def env_str(name, default=""):
    return os.environ.get(name, default) or default


def env_int(name, default):
    return int(env_str(name, str(default)))


def env_optional(name):
    value = os.environ.get(name)
    return None if value is None or value == "" else value


def require_env(name):
    value = env_str(name).strip()
    if not value:
        raise RuntimeError(f"请先设置系统环境变量 {name}")
    return value


MYSQL_HOST = env_str("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = env_int("MYSQL_PORT", 3306)
MYSQL_USER = env_str("MYSQL_USER", "root")
MYSQL_PASSWORD = require_env("MYSQL_PASSWORD")
MYSQL_DATABASE = env_str("MYSQL_DATABASE", "shixun")
MYSQL_STATISTICS_TABLE = env_str("MYSQL_STATISTICS_TABLE", "tongji_fenxi_jieguo")

REDIS_HOST = env_str("REDIS_HOST", "127.0.0.1")
REDIS_PORT = env_int("REDIS_PORT", 6379)
REDIS_PASSWORD = env_optional("REDIS_PASSWORD")
REDIS_DATABASE = env_int("REDIS_DATABASE", 0)

SPARK_MASTER = "local[2]"
SPARK_SHUFFLE_PARTITIONS = "4"

# 2. 导入依赖和公共辅助函数。
from datetime import date, datetime
from decimal import Decimal
import json
import math
import pymysql
import redis
from pyspark.sql import SparkSession, functions as F


def mysql_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=False,
        connect_timeout=5,
    )


def redis_connection():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DATABASE,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=5,
    )


def json_value(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def rounded(value, digits=2):
    value = json_value(value)
    return None if value is None else round(float(value), digits)


UPDATED_AT = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_result(result_type, data):
    return {
        "type": result_type,
        "scope_id": SCOPE_ID,
        "keyword": KEYWORD,
        "updated_at": UPDATED_AT,
        "data": data,
    }

# 3. 创建支持 Hive 的 SparkSession。
if DATA_SOURCE not in {"hive", "hdfs"}:
    raise ValueError('DATA_SOURCE 只能设置为 "hive" 或 "hdfs"。')

active_session = SparkSession.getActiveSession()
if active_session is not None:
    active_session.stop()

spark = (
    SparkSession.builder
    .appName("ZhaopinDashboardStatistics")
    .master(SPARK_MASTER)
    .config("spark.hadoop.fs.defaultFS", HDFS_URI)
    .config("spark.sql.shuffle.partitions", SPARK_SHUFFLE_PARTITIONS)
    .enableHiveSupport()
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")
print("Spark 版本:", spark.version)
print("数据源模式:", DATA_SOURCE)

# 4. 检查 Hive/HDFS、MySQL 和 Redis 连接。
if DATA_SOURCE == "hive":
    database_names = {row.namespace for row in spark.sql("SHOW DATABASES").collect()}
    if HIVE_DATABASE not in database_names:
        raise RuntimeError(f"Hive 数据库不存在: {HIVE_DATABASE}")
    table_names = {row.tableName for row in spark.sql(f"SHOW TABLES IN {HIVE_DATABASE}").collect()}
    missing_tables = {HIVE_JOB_TABLE, HIVE_SKILL_TABLE} - table_names
    if missing_tables:
        raise RuntimeError(f"Hive 数据表不存在: {sorted(missing_tables)}")
else:
    filesystem = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
    path_class = spark._jvm.org.apache.hadoop.fs.Path
    missing_paths = [path for path in [HDFS_JOB_PATH, HDFS_SKILL_PATH] if not filesystem.exists(path_class(path))]
    if missing_paths:
        raise RuntimeError(f"HDFS ORC 路径不存在: {missing_paths}")

mysql_conn = mysql_connection()
try:
    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.execute("SHOW TABLES LIKE %s", (MYSQL_STATISTICS_TABLE,))
        if cursor.fetchone() is None:
            raise RuntimeError(f"MySQL 统计表不存在，请先运行 sql/创建MySQL数据表.py: {MYSQL_STATISTICS_TABLE}")
    print("MySQL 连接正常，统计表已存在。")
finally:
    mysql_conn.close()

try:
    redis_client = redis_connection()
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("Redis 连接正常。")
except Exception as exc:
    REDIS_AVAILABLE = False
    redis_client = None
    print("Redis 当前不可用，统计仍会继续并写入 MySQL:", repr(exc))

# 5. 读取岗位明细；读取失败时不自动改用另一种数据源。
if DATA_SOURCE == "hive":
    job_df = spark.table(f"{HIVE_DATABASE}.{HIVE_JOB_TABLE}")
else:
    job_df = spark.read.option("basePath", HDFS_URI + HDFS_JOB_PATH).orc(HDFS_URI + HDFS_JOB_PATH)

job_df = (
    job_df
    .where(F.col("guanjianci_daima") == KEYWORD_CODE)
    .dropDuplicates(["gangwei_weiyi_biaoshi"])
    .cache()
)
JOB_COUNT = job_df.count()
if JOB_COUNT == 0:
    raise ValueError(f"岗位明细没有指定关键词的数据: keyword_code={KEYWORD_CODE}, scope_id={SCOPE_ID}")
print("岗位明细记录数:", JOB_COUNT)

# 6. 读取技能明细。
if DATA_SOURCE == "hive":
    skill_df = spark.table(f"{HIVE_DATABASE}.{HIVE_SKILL_TABLE}")
else:
    skill_df = spark.read.option("basePath", HDFS_URI + HDFS_SKILL_PATH).orc(HDFS_URI + HDFS_SKILL_PATH)

skill_df = (
    skill_df
    .where(F.col("guanjianci_daima") == KEYWORD_CODE)
    .cache()
)
SKILL_ROW_COUNT = skill_df.count()
if SKILL_ROW_COUNT == 0:
    raise ValueError(f"技能明细没有指定关键词的数据: keyword_code={KEYWORD_CODE}, scope_id={SCOPE_ID}")
print("技能明细记录数:", SKILL_ROW_COUNT)

# 7. 检查统计必需字段和基础数据质量。
REQUIRED_JOB_COLUMNS = {
    "guanjianci", "guanjianci_daima", "guanjianci_biaoshi", "gangwei_weiyi_biaoshi",
    "laiyuan_chengshi", "zuidi_nianxin_wan", "zuigao_nianxin_wan", "xueli_yaoqiu",
    "jingyan_yaoqiu", "gongsi_mingcheng", "gongsi_guimo", "gongsi_xingzhi",
    "rongzi_jieduan", "hangye", "fabu_riqi",
}
REQUIRED_SKILL_COLUMNS = {
    "guanjianci_daima", "guanjianci_biaoshi", "gangwei_weiyi_biaoshi", "jineng_mingcheng"
}
missing_job_columns = sorted(REQUIRED_JOB_COLUMNS - set(job_df.columns))
missing_skill_columns = sorted(REQUIRED_SKILL_COLUMNS - set(skill_df.columns))
if missing_job_columns or missing_skill_columns:
    raise ValueError(f"缺少必需字段，岗位表={missing_job_columns}，技能表={missing_skill_columns}")

job_df = job_df.withColumn(
    "_nianxin_zhongzhi",
    (F.col("zuidi_nianxin_wan").cast("double") + F.col("zuigao_nianxin_wan").cast("double")) / F.lit(2.0),
)
VALID_SALARY = (
    F.col("zuidi_nianxin_wan").cast("double").isNotNull()
    & F.col("zuigao_nianxin_wan").cast("double").isNotNull()
    & (F.col("zuidi_nianxin_wan").cast("double") > 0)
    & (F.col("zuigao_nianxin_wan").cast("double") > 0)
)
VALID_SALARY_COUNT = job_df.where(VALID_SALARY).count()
print("有有效薪资数据的岗位数:", VALID_SALARY_COUNT)

# 8. 计算岗位概览。
summary_row = job_df.agg(
    F.countDistinct("gangwei_weiyi_biaoshi").alias("job_count"),
    F.countDistinct(F.when(F.trim(F.col("gongsi_mingcheng")) != "", F.col("gongsi_mingcheng"))).alias("company_count"),
    F.countDistinct(F.when(F.trim(F.col("laiyuan_chengshi")) != "", F.col("laiyuan_chengshi"))).alias("city_count"),
    F.avg(F.when(VALID_SALARY, F.col("zuidi_nianxin_wan").cast("double"))).alias("avg_min_salary"),
    F.avg(F.when(VALID_SALARY, F.col("zuigao_nianxin_wan").cast("double"))).alias("avg_max_salary"),
    F.avg(F.when(VALID_SALARY, F.col("_nianxin_zhongzhi"))).alias("avg_mid_salary"),
).first()

summary_data = {
    "job_count": int(summary_row["job_count"]),
    "company_count": int(summary_row["company_count"]),
    "city_count": int(summary_row["city_count"]),
    "average_min_annual_salary_wan": rounded(summary_row["avg_min_salary"]),
    "average_max_annual_salary_wan": rounded(summary_row["avg_max_salary"]),
    "average_annual_salary_wan": rounded(summary_row["avg_mid_salary"]),
    "salary_job_count": int(VALID_SALARY_COUNT),
    "data_updated_at": UPDATED_AT,
}
summary_result = make_result("summary", summary_data)
summary_data

# 9. 计算城市岗位数量、平均年薪和最高年薪。
city_rows = (
    job_df
    .withColumn("_city", F.when(F.trim(F.col("laiyuan_chengshi")) == "", F.lit("未知")).otherwise(F.col("laiyuan_chengshi")))
    .groupBy("_city")
    .agg(
        F.countDistinct("gangwei_weiyi_biaoshi").alias("job_count"),
        F.avg(F.when(VALID_SALARY, F.col("_nianxin_zhongzhi"))).alias("average_salary"),
        F.max(F.when(VALID_SALARY, F.col("zuigao_nianxin_wan").cast("double"))).alias("max_salary"),
    )
    .orderBy(F.desc("job_count"), F.asc("_city"))
    .collect()
)
city_data = {
    "categories": [row["_city"] for row in city_rows],
    "job_counts": [int(row["job_count"]) for row in city_rows],
    "average_salary_wan": [rounded(row["average_salary"]) for row in city_rows],
    "max_salary_wan": [rounded(row["max_salary"]) for row in city_rows],
}
city_result = make_result("city", city_data)
city_data

# 10. 使用年薪中间值计算薪资区间分布，边界采用左闭右开。
salary_bucket = (
    F.when(~VALID_SALARY, F.lit("未知"))
    .when(F.col("_nianxin_zhongzhi") < 10, F.lit("0～10万"))
    .when(F.col("_nianxin_zhongzhi") < 20, F.lit("10～20万"))
    .when(F.col("_nianxin_zhongzhi") < 30, F.lit("20～30万"))
    .when(F.col("_nianxin_zhongzhi") < 50, F.lit("30～50万"))
    .otherwise(F.lit("50万以上"))
)
salary_order = ["0～10万", "10～20万", "20～30万", "30～50万", "50万以上", "未知"]
salary_counts = {
    row["bucket"]: int(row["count"])
    for row in job_df.withColumn("bucket", salary_bucket).groupBy("bucket").count().collect()
}
salary_data = {"categories": salary_order, "values": [salary_counts.get(name, 0) for name in salary_order]}
salary_result = make_result("salary", salary_data)
salary_data

# 11. 计算学历和经验分布；仅统一常见写法，其他原始分类继续保留。
education_text = F.trim(F.coalesce(F.col("xueli_yaoqiu"), F.lit("")))
education_category = (
    F.when(education_text == "", "未知")
    .when(education_text.contains("不限"), "学历不限")
    .when(education_text.contains("博士"), "博士")
    .when(education_text.contains("硕士"), "硕士")
    .when(education_text.contains("本科"), "本科")
    .when(education_text.rlike("大专|专科"), "大专")
    .otherwise(education_text)
)
experience_text = F.trim(F.coalesce(F.col("jingyan_yaoqiu"), F.lit("")))
experience_category = (
    F.when(experience_text == "", "未知")
    .when(experience_text.rlike("不限|无经验"), "经验不限")
    .when(experience_text.rlike("1年以下|一年以下|应届|在校"), "1年以下")
    .when(experience_text.rlike("1[-～~至]3年"), "1～3年")
    .when(experience_text.rlike("3[-～~至]5年"), "3～5年")
    .when(experience_text.rlike("5[-～~至]10年"), "5～10年")
    .when(experience_text.rlike("10年以上"), "10年以上")
    .otherwise(experience_text)
)


def distribution_from_expression(expression, fixed_order=None):
    rows = job_df.withColumn("category", expression).groupBy("category").count().collect()
    counts = {row["category"]: int(row["count"]) for row in rows}
    if fixed_order is None:
        categories = [item[0] for item in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
    else:
        categories = list(fixed_order) + sorted(name for name in counts if name not in fixed_order)
    return {"categories": categories, "values": [counts.get(name, 0) for name in categories]}


education_data = distribution_from_expression(education_category, ["大专", "本科", "硕士", "博士", "学历不限", "未知"])
experience_data = distribution_from_expression(experience_category, ["经验不限", "1年以下", "1～3年", "3～5年", "5～10年", "10年以上", "未知"])
education_result = make_result("education", education_data)
experience_result = make_result("experience", experience_data)
{"education": education_data, "experience": experience_data}

# 12. 计算公司规模、性质、融资阶段和招聘岗位最多的公司 Top15。
def column_distribution(column_name):
    expression = F.when(F.trim(F.coalesce(F.col(column_name), F.lit(""))) == "", "未知").otherwise(F.trim(F.col(column_name)))
    return distribution_from_expression(expression)


company_size_data = column_distribution("gongsi_guimo")
company_type_data = column_distribution("gongsi_xingzhi")
financing_data = column_distribution("rongzi_jieduan")
top_company_rows = (
    job_df
    .where(F.trim(F.coalesce(F.col("gongsi_mingcheng"), F.lit(""))) != "")
    .groupBy("gongsi_mingcheng")
    .agg(F.countDistinct("gangwei_weiyi_biaoshi").alias("job_count"))
    .orderBy(F.desc("job_count"), F.asc("gongsi_mingcheng"))
    .limit(15)
    .collect()
)
top_companies_data = {
    "categories": [row["gongsi_mingcheng"] for row in top_company_rows],
    "values": [int(row["job_count"]) for row in top_company_rows],
}
company_size_result = make_result("company_size", company_size_data)
company_type_result = make_result("company_type", company_type_data)
financing_result = make_result("financing", financing_data)
top_companies_result = make_result("top_companies", top_companies_data)
top_companies_data

# 13. 计算行业 Top15，其余行业合并为“其他”。
industry_expression = F.when(F.trim(F.coalesce(F.col("hangye"), F.lit(""))) == "", "未知").otherwise(F.trim(F.col("hangye")))
industry_rows = (
    job_df.withColumn("industry", industry_expression)
    .groupBy("industry")
    .agg(F.countDistinct("gangwei_weiyi_biaoshi").alias("job_count"))
    .orderBy(F.desc("job_count"), F.asc("industry"))
    .collect()
)
industry_top = industry_rows[:15]
industry_other_count = sum(int(row["job_count"]) for row in industry_rows[15:])
industry_categories = [row["industry"] for row in industry_top]
industry_values = [int(row["job_count"]) for row in industry_top]
if industry_other_count:
    industry_categories.append("其他")
    industry_values.append(industry_other_count)
industry_data = {"categories": industry_categories, "values": industry_values}
industry_result = make_result("industry", industry_data)
industry_data

# 14. 计算数据中最近 30 天的发布时间趋势。
max_publish_date = job_df.agg(F.max("fabu_riqi").alias("max_date")).first()["max_date"]
if max_publish_date is None:
    publish_trend_data = {"categories": [], "values": []}
else:
    trend_rows = (
        job_df
        .where(F.col("fabu_riqi").isNotNull())
        .where(F.col("fabu_riqi") >= F.date_sub(F.lit(max_publish_date), 29))
        .groupBy("fabu_riqi")
        .agg(F.countDistinct("gangwei_weiyi_biaoshi").alias("job_count"))
        .orderBy("fabu_riqi")
        .collect()
    )
    publish_trend_data = {
        "categories": [row["fabu_riqi"].isoformat() for row in trend_rows],
        "values": [int(row["job_count"]) for row in trend_rows],
    }
publish_trend_result = make_result("publish_trend", publish_trend_data)
publish_trend_data

# 15. 按“岗位 ID + 技能名称”去重后计算热门技能 Top20。
deduplicated_skill_df = (
    skill_df
    .withColumn("_skill", F.trim(F.coalesce(F.col("jineng_mingcheng"), F.lit(""))))
    .where(F.col("_skill") != "")
    .dropDuplicates(["gangwei_weiyi_biaoshi", "_skill"])
)
skill_rows = (
    deduplicated_skill_df
    .groupBy("_skill")
    .agg(F.countDistinct("gangwei_weiyi_biaoshi").alias("job_count"))
    .orderBy(F.desc("job_count"), F.asc("_skill"))
    .limit(20)
    .collect()
)
skills_data = {
    "categories": [row["_skill"] for row in skill_rows],
    "values": [int(row["job_count"]) for row in skill_rows],
}
skills_result = make_result("skills", skills_data)
skills_data

# 16. 生成统一 JSON 结果，并执行统计口径校验。
STATISTICS_RESULTS = {
    result["type"]: result
    for result in [
        summary_result, city_result, salary_result, education_result, experience_result,
        company_size_result, company_type_result, financing_result, top_companies_result,
        industry_result, publish_trend_result, skills_result,
    ]
}

expected_job_count = summary_data["job_count"]
assert expected_job_count == JOB_COUNT, "岗位总数不等于岗位 ID 去重数量"
assert sum(city_data["job_counts"]) == expected_job_count, "城市岗位数之和不等于岗位总数"
assert sum(salary_data["values"]) == expected_job_count, "薪资分布之和不等于岗位总数"
assert sum(education_data["values"]) == expected_job_count, "学历分布之和不等于岗位总数"
assert sum(experience_data["values"]) == expected_job_count, "经验分布之和不等于岗位总数"
assert "未知" in salary_data["categories"], "薪资分布缺少未知分类"
assert deduplicated_skill_df.count() <= SKILL_ROW_COUNT, "技能去重结果异常"

STATISTICS_JSON = {
    result_type: json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    for result_type, result in STATISTICS_RESULTS.items()
}
print("统计类型:", list(STATISTICS_RESULTS))
print("全部统计口径校验通过。")

# 17. 使用事务和 ON DUPLICATE KEY UPDATE 写入 MySQL。
UPSERT_SQL = f"""
INSERT INTO `{MYSQL_STATISTICS_TABLE}`
(`guanjianci_biaoshi`, `guanjianci`, `tongji_leixing`, `jieguo_json`, `gengxin_shijian`)
VALUES (%s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
`guanjianci` = VALUES(`guanjianci`),
`jieguo_json` = VALUES(`jieguo_json`),
`gengxin_shijian` = VALUES(`gengxin_shijian`)
"""
mysql_rows = [
    (SCOPE_ID, KEYWORD, result_type, STATISTICS_JSON[result_type], UPDATED_AT)
    for result_type in STATISTICS_RESULTS
]
mysql_conn = mysql_connection()
try:
    with mysql_conn.cursor() as cursor:
        cursor.executemany(UPSERT_SQL, mysql_rows)
    mysql_conn.commit()
    MYSQL_WRITE_SUCCEEDED = True
    print("MySQL 已提交统计结果，类型数量:", len(mysql_rows))
except Exception:
    mysql_conn.rollback()
    MYSQL_WRITE_SUCCEEDED = False
    raise
finally:
    mysql_conn.close()

# 18. MySQL 提交成功后，使用 Redis Pipeline 覆盖全部统计 Key（不设置 TTL）。
REDIS_KEY_SUFFIX = {
    "summary": "summary",
    "city": "city",
    "salary": "salary",
    "education": "education",
    "experience": "experience",
    "company_size": "company_size",
    "company_type": "company_type",
    "financing": "financing",
    "top_companies": "top_companies",
    "industry": "industry",
    "publish_trend": "publish_trend",
    "skills": "skills",
}

if not MYSQL_WRITE_SUCCEEDED:
    raise RuntimeError("MySQL 未成功提交，禁止写入 Redis。")

try:
    redis_client = redis_connection()
    pipeline = redis_client.pipeline(transaction=False)
    stale_cache_patterns = [
        f'zhaopin:jobs:{SCOPE_ID}:*',
        f'zhaopin:filters:{SCOPE_ID}',
        'zhaopin:job:*',
    ]
    stale_cache_keys = set()
    for pattern in stale_cache_patterns:
        stale_cache_keys.update(redis_client.scan_iter(match=pattern, count=500))
    if stale_cache_keys:
        pipeline.delete(*sorted(stale_cache_keys))
    for result_type, result_json in STATISTICS_JSON.items():
        key = f"zhaopin:dashboard:{REDIS_KEY_SUFFIX[result_type]}:{SCOPE_ID}"
        pipeline.set(key, result_json)
    pipeline.execute()
    REDIS_WRITE_SUCCEEDED = True
    print("Redis 已同步统计 Key，数量:", len(STATISTICS_JSON))
    print("已清理过期岗位查询缓存，数量:", len(stale_cache_keys))
except Exception as exc:
    REDIS_WRITE_SUCCEEDED = False
    print("Redis 写入失败；MySQL 已提交，不执行回滚:", repr(exc))

# 19. 从 MySQL 和 Redis 回读，验证 JSON、唯一性和内容一致性。
mysql_conn = mysql_connection()
try:
    with mysql_conn.cursor() as cursor:
        cursor.execute(
            f"SELECT tongji_leixing, jieguo_json FROM `{MYSQL_STATISTICS_TABLE}` WHERE guanjianci_biaoshi = %s",
            (SCOPE_ID,),
        )
        mysql_back = {result_type: payload for result_type, payload in cursor.fetchall()}
finally:
    mysql_conn.close()

assert set(mysql_back) >= set(STATISTICS_JSON), "MySQL 回读缺少统计类型"
for result_type, expected_json in STATISTICS_JSON.items():
    parsed = json.loads(mysql_back[result_type])
    assert parsed["type"] == result_type
    assert parsed["scope_id"] == SCOPE_ID
    assert json.loads(expected_json) == parsed
print("MySQL 回读和 JSON 解析验证通过。")

if REDIS_WRITE_SUCCEEDED:
    redis_client = redis_connection()
    for result_type, expected_json in STATISTICS_JSON.items():
        key = f"zhaopin:dashboard:{REDIS_KEY_SUFFIX[result_type]}:{SCOPE_ID}"
        actual_json = redis_client.get(key)
        assert actual_json is not None, f"Redis Key 不存在: {key}"
        assert json.loads(actual_json) == json.loads(expected_json), f"Redis 与 MySQL 内容不一致: {result_type}"
    print("Redis Key 与 MySQL 统计结果一致。")
else:
    print("Redis 不可用，已按降级规则仅保留 MySQL 结果。")

print("统计任务完成，更新时间:", UPDATED_AT)
print("岗位数:", summary_data["job_count"], "技能明细数:", SKILL_ROW_COUNT)
job_df.unpersist()
skill_df.unpersist()
spark.stop()
