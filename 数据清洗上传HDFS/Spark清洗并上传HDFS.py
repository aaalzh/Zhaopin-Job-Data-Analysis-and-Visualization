#!/usr/bin/env python
# coding: utf-8

# MySQL 原始数据读取、Spark 清洗、写入 MySQL 并上传 HDFS
# 本脚本使用关键词代码生成关键词标识。统一城市列表只作为采集清单；每个关键词只保留一份清洗快照。输出字段、MySQL 表和 Hive 字段全部使用小写拼音加下划线命名。
# 1. 参数配置
# `KEYWORD`、`KEYWORD_PATH_CODE` 和 `CITY_LIST` 必须与爬虫脚本一致。
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
import hashlib
import os
import re
import shutil
import subprocess
import sys

import pandas as pd
import pymysql
from sqlalchemy import create_engine, text

KEYWORD = '数据分析'
KEYWORD_PATH_CODE = 'shuju_fenxi'
CITY_LIST = [
    '北京', '上海', '广州', '深圳', '天津', '武汉', '西安', '成都',
    '大连', '长春', '沈阳', '南京', '济南', '青岛', '杭州', '苏州',
    '无锡', '宁波', '重庆', '郑州', '长沙', '福州', '厦门', '哈尔滨',
    '东莞', '佛山', '珠海', '惠州', '中山', '江门',
    '合肥', '南昌', '泉州', '温州', '嘉兴', '常州',
    '扬州', '绍兴', '金华', '徐州', '南通',
    '昆明', '贵阳', '南宁', '海口',
    '兰州', '太原', '石家庄', '呼和浩特',
    '乌鲁木齐', '拉萨', '银川', '西宁',
    '唐山', '烟台', '潍坊', '临沂', '洛阳', '宜昌', '襄阳'
]

# 必须与爬虫脚本保持一致；城市代码来自智联招聘 citymap。
CITY_CODE_MAP = {
    '全国': '489',
    '北京': '530', '上海': '538', '天津': '531', '重庆': '551',
    '广州': '763', '深圳': '765', '武汉': '736', '西安': '854',
    '成都': '801', '大连': '600', '长春': '613', '沈阳': '599',
    '南京': '635', '济南': '702', '青岛': '703', '杭州': '653',
    '苏州': '639', '无锡': '636', '宁波': '654', '郑州': '719',
    '长沙': '749', '福州': '681', '厦门': '682', '哈尔滨': '622',
    '东莞': '779', '佛山': '768', '珠海': '766', '惠州': '773',
    '中山': '780', '江门': '769', '合肥': '664', '南昌': '691',
    '泉州': '685', '温州': '655', '嘉兴': '656', '常州': '638',
    '扬州': '645', '绍兴': '658', '金华': '659', '徐州': '637',
    '南通': '641', '昆明': '831', '贵阳': '822', '南宁': '785',
    '海口': '799', '兰州': '864', '太原': '576', '石家庄': '565',
    '呼和浩特': '587', '乌鲁木齐': '890', '拉萨': '847', '银川': '886',
    '西宁': '878', '唐山': '566', '烟台': '707', '潍坊': '708',
    '临沂': '714', '洛阳': '721', '宜昌': '739', '襄阳': '740'
}

def env_str(name, default=''):
    return os.environ.get(name, default) or default


def env_int(name, default):
    return int(env_str(name, str(default)))


def require_env(name):
    value = env_str(name).strip()
    if not value:
        raise RuntimeError(f'请先设置系统环境变量 {name}')
    return value


MYSQL_HOST = env_str('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = env_int('MYSQL_PORT', 3306)
MYSQL_USER = env_str('MYSQL_USER', 'root')
MYSQL_PASSWORD = require_env('MYSQL_PASSWORD')
MYSQL_DATABASE = env_str('MYSQL_DATABASE', 'shixun')
RAW_JOB_TABLE = 'yuan_shi_gangwei_xinxi'
RAW_COMPANY_TABLE = 'yuan_shi_gongsi_xinxi'
RAW_RECRUITER_TABLE = 'yuan_shi_zhaopin_fuzeren_xinxi'
CLEAN_JOB_TABLE = 'qingxi_gangwei_mingxi'
CLEAN_COMPANY_TABLE = 'qingxi_gongsi_xinxi'
CLEAN_RECRUITER_TABLE = 'qingxi_zhaopin_fuzeren_xinxi'
CLEAN_LOG_TABLE = 'qingxi_yunxing_rizhi'

HDFS_URI = 'hdfs://localhost:9000'
HDFS_USER = '10967'
HDFS_PROJECT_DIR = f'{HDFS_URI}/user/{HDFS_USER}/zhilian_zhaopin'
HDFS_CLEAN_BASE_DIR = f'{HDFS_PROJECT_DIR}/qingxi_jieguo'
HDFS_HIVE_INPUT_DIR = f'{HDFS_PROJECT_DIR}/shucang/yuan_shi_gangwei_qingxi'
HIVE_PARTITION_COLUMNS = ['guanjianci_daima']
SPARK_MASTER = 'local[2]'

MYSQL_JDBC_DRIVER = 'com.mysql.cj.jdbc.Driver'
MYSQL_JDBC_JAR = os.environ.get('MYSQL_JDBC_JAR', '')

METADATA_COLUMNS = [
    'yuan_shi_gangwei_bianhao', 'yunxing_biaoshi', 'guanjianci', 'guanjianci_daima',
    'guanjianci_biaoshi', 'chengshi_liebiao', 'chengshi_daima_liebiao',
    'laiyuan_chengshi', 'gangwei_weiyi_biaoshi'
]
TARGET_COLUMNS = [
    'zhiwei_mingcheng', 'xinzi', 'xinzi_leixing', 'xinzi_fafang_cishu',
    'gongzuo_chengshi', 'xingzhengqu', 'shangquan_jiedao', 'gongzuo_didian',
    'xiangxi_dizhi', 'jingdu', 'weidu', 'jingyan_yaoqiu', 'xueli_yaoqiu',
    'gongzuo_leixing', 'gongzuo_moshi', 'zhiwei_leibie', 'gongsi_mingcheng',
    'gongsi_guimo', 'gongsi_xingzhi', 'rongzi_jieduan', 'hangye', 'fabu_shijian',
    'shouci_fabu_shijian', 'fabu_riqi_wenben', 'shifou_xin_zhiwei', 'zhaopin_renshu',
    'zhaopin_fuzeren_zhuangtai', 'zhaopin_fuzeren_huoyue_biaoqian',
    'zhiwei_biaoqian_huizong', 'jineng_biaoqian', 'fuli_biaoqian', 'fuli_mingxi',
    'gongzuo_shijian', 'baogao_baozhang_xiang', 'zhiwei_miaoshu',
    'zhiwei_liangdian', 'zhiwei_zhaiyao', 'renzheng_shouhu_xinxi'
]
DROP_COLUMNS = [
    'xinzi_leixing', 'xinzi_fafang_cishu', 'gongzuo_chengshi', 'xingzhengqu',
    'shangquan_jiedao', 'xiangxi_dizhi', 'jingdu', 'weidu', 'fuli_biaoqian',
    'fuli_mingxi', 'gongzuo_shijian', 'baogao_baozhang_xiang',
    'shouci_fabu_shijian', 'fabu_riqi_wenben', 'shifou_xin_zhiwei',
    'zhaopin_renshu', 'zhiwei_liangdian', 'zhiwei_zhaiyao',
    'zhiwei_biaoqian_huizong', 'renzheng_shouhu_xinxi'
]
FINAL_COLUMNS = [
    'zhiwei_mingcheng', 'zuidi_xinzi', 'zuigao_xinzi', 'gongzuo_didian',
    'jingyan_yaoqiu', 'xueli_yaoqiu', 'gongzuo_leixing', 'gongzuo_moshi',
    'zhiwei_leibie', 'gongsi_mingcheng', 'gongsi_guimo', 'gongsi_xingzhi',
    'rongzi_jieduan', 'hangye', 'fabu_shijian', 'zhaopin_fuzeren_zhuangtai',
    'zhaopin_fuzeren_huoyue_biaoqian', 'jineng_biaoqian', 'zhiwei_miaoshu'
]
CLEAN_JOB_COLUMNS = METADATA_COLUMNS + FINAL_COLUMNS
CLEAN_COMPANY_COLUMNS = [
    'yunxing_biaoshi', 'guanjianci', 'guanjianci_daima', 'guanjianci_biaoshi',
    'chengshi_liebiao', 'chengshi_daima_liebiao', 'laiyuan_chengshi',
    'gongsi_weiyi_biaoshi', 'gongsi_mingcheng', 'gongsi_guimo', 'gongsi_xingzhi',
    'rongzi_jieduan', 'hangye'
]
CLEAN_RECRUITER_COLUMNS = [
    'yunxing_biaoshi', 'guanjianci', 'guanjianci_daima', 'guanjianci_biaoshi',
    'chengshi_liebiao', 'chengshi_daima_liebiao', 'laiyuan_chengshi',
    'gangwei_weiyi_biaoshi', 'zhaopin_fuzeren_weiyi_biaoshi',
    'zhiwei_mingcheng', 'gongsi_mingcheng', 'zhaopin_fuzeren_zhuangtai',
    'zhaopin_fuzeren_huoyue_biaoqian'
]

DEFAULT_MONTHS = 12
WORK_DAYS_PER_MONTH = 25
HOURS_PER_DAY = 8
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable


def build_collection_scope(keyword, keyword_code, city_list):
    city_by_code = {}
    for city in city_list:
        code = CITY_CODE_MAP[city]
        city_by_code[str(code)] = str(city).strip()
    ordered = sorted(city_by_code.items(), key=lambda item: item[0])
    codes = [item[0] for item in ordered]
    names = [item[1] for item in ordered]
    return {
        'guanjianci_biaoshi': str(keyword_code).strip(),
        'chengshi_liebiao': ','.join(names),
        'chengshi_daima_liebiao': ','.join(codes),
    }


def find_project_root():
    current = Path.cwd().resolve()
    candidates = [current] + list(current.parents)
    for path in candidates:
        if (path / 'sql').exists() and (path / '数据清洗上传HDFS').exists():
            return path
    for path in candidates:
        if (path / '.git').exists():
            return path
    raise FileNotFoundError('没有找到项目根目录，请在项目根目录或脚本目录运行。')


def find_spark_home():
    configured = os.environ.get('SPARK_HOME')
    if configured and (Path(configured) / 'python').exists():
        return Path(configured).resolve()
    command = shutil.which('spark-submit') or shutil.which('spark-submit.cmd')
    if command:
        return Path(command).resolve().parent.parent
    raise FileNotFoundError('没有找到 Spark。')


def configure_pyspark_path(spark_home):
    candidates = [spark_home / 'python', *sorted((spark_home / 'python' / 'lib').glob('py4j-*.zip'))]
    for item in candidates:
        value = str(item)
        if value not in sys.path:
            sys.path.insert(0, value)


def find_mysql_jdbc_jar(spark_home, configured=''):
    if configured:
        path = Path(configured)
        if path.exists():
            return str(path.resolve())
        raise FileNotFoundError(f'MYSQL_JDBC_JAR 不存在: {configured}')
    candidates = sorted((spark_home / 'jars').glob('mysql-connector-j-*.jar'))
    if not candidates:
        raise FileNotFoundError('Spark jars 中没有 MySQL JDBC 驱动。')
    return str(candidates[0].resolve())


PROJECT_ROOT = find_project_root()
SPARK_HOME = find_spark_home()
configure_pyspark_path(SPARK_HOME)
MYSQL_JDBC_JAR = find_mysql_jdbc_jar(SPARK_HOME, MYSQL_JDBC_JAR)
SCOPE = build_collection_scope(KEYWORD, KEYWORD_PATH_CODE, CITY_LIST)
MYSQL_JDBC_URL = f'jdbc:mysql://{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai'

from pyspark.sql import SparkSession, functions as F

print('关键词标识:', SCOPE['guanjianci_biaoshi'])
print('关键词:', KEYWORD)
print('统一城市列表:', SCOPE['chengshi_liebiao'])
print('MySQL原始表:', RAW_JOB_TABLE, RAW_COMPANY_TABLE, RAW_RECRUITER_TABLE)
print('MySQL清洗表:', CLEAN_JOB_TABLE, CLEAN_COMPANY_TABLE, CLEAN_RECRUITER_TABLE)
print('Hive输入目录:', HDFS_HIVE_INPUT_DIR)


# 2. 创建 SparkSession
def create_spark_session(app_name):
    active = SparkSession.getActiveSession()
    if active is not None:
        active.stop()
    builder = (
        SparkSession.builder.appName(app_name).master(SPARK_MASTER)
        .config('spark.hadoop.fs.defaultFS', HDFS_URI)
        .config('spark.pyspark.python', sys.executable)
        .config('spark.pyspark.driver.python', sys.executable)
        .config('spark.sql.shuffle.partitions', '2')
        .config('spark.jars', MYSQL_JDBC_JAR)
        .config('spark.driver.extraClassPath', MYSQL_JDBC_JAR)
        .config('spark.executor.extraClassPath', MYSQL_JDBC_JAR)
    )
    return builder.getOrCreate()


spark = create_spark_session('ZhaopinScopeSnapshotCleaning')
print('Spark版本:', spark.version)


# 3. 按关键词从 MySQL 原始表读取
def qi(name):
    return f'{chr(96)}{name}{chr(96)}'


def mysql_literal(value):
    value = '' if value is None else str(value)
    return "'" + value.replace('\\', '\\\\').replace("'", "''") + "'"


def mysql_jdbc_options():
    return {'url': MYSQL_JDBC_URL, 'driver': MYSQL_JDBC_DRIVER, 'user': MYSQL_USER, 'password': MYSQL_PASSWORD}


def build_raw_mysql_query(scope_id):
    def j_col(name):
        return f'j.{qi(name)} AS {qi(name)}'
    def c_col(name):
        return f'COALESCE(c.{qi(name)}, {mysql_literal("")}) AS {qi(name)}'
    def r_col(name):
        return f'COALESCE(r.{qi(name)}, {mysql_literal("")}) AS {qi(name)}'

    columns = [
        'j.zizeng_bianhao AS yuan_shi_gangwei_bianhao',
        'j.yunxing_biaoshi', 'j.guanjianci', 'j.guanjianci_daima',
        'j.guanjianci_biaoshi', 'j.chengshi_liebiao', 'j.chengshi_daima_liebiao',
        'j.laiyuan_chengshi', 'j.gangwei_weiyi_biaoshi',
        j_col('zhiwei_mingcheng'), j_col('xinzi'), j_col('xinzi_leixing'),
        j_col('xinzi_fafang_cishu'), j_col('gongzuo_chengshi'), j_col('xingzhengqu'),
        j_col('shangquan_jiedao'), j_col('gongzuo_didian'), j_col('xiangxi_dizhi'),
        j_col('jingdu'), j_col('weidu'), j_col('jingyan_yaoqiu'), j_col('xueli_yaoqiu'),
        j_col('gongzuo_leixing'), j_col('gongzuo_moshi'), j_col('zhiwei_leibie'),
        j_col('gongsi_mingcheng'), c_col('gongsi_guimo'), c_col('gongsi_xingzhi'),
        c_col('rongzi_jieduan'), c_col('hangye'), j_col('fabu_shijian'),
        j_col('shouci_fabu_shijian'), j_col('fabu_riqi_wenben'), j_col('shifou_xin_zhiwei'),
        j_col('zhaopin_renshu'), r_col('zhaopin_fuzeren_zhuangtai'),
        r_col('zhaopin_fuzeren_huoyue_biaoqian'), j_col('zhiwei_biaoqian_huizong'),
        j_col('jineng_biaoqian'), j_col('fuli_biaoqian'), j_col('fuli_mingxi'),
        j_col('gongzuo_shijian'), j_col('baogao_baozhang_xiang'), j_col('zhiwei_miaoshu'),
        j_col('zhiwei_liangdian'), j_col('zhiwei_zhaiyao'), j_col('renzheng_shouhu_xinxi')
    ]
    company_join = (
        f'LEFT JOIN {RAW_COMPANY_TABLE} c ON c.yunxing_biaoshi = j.yunxing_biaoshi '
        f'AND c.guanjianci_biaoshi = j.guanjianci_biaoshi '
        f'AND c.laiyuan_chengshi <=> j.laiyuan_chengshi '
        f'AND c.gongsi_mingcheng <=> j.gongsi_mingcheng'
    )
    recruiter_join = (
        f'LEFT JOIN {RAW_RECRUITER_TABLE} r ON r.yunxing_biaoshi = j.yunxing_biaoshi '
        f'AND r.gangwei_weiyi_biaoshi <=> j.gangwei_weiyi_biaoshi'
    )
    where_clause = f'j.guanjianci_biaoshi = {mysql_literal(scope_id)}'
    return f'(SELECT {", ".join(columns)} FROM {RAW_JOB_TABLE} j {company_join} {recruiter_join} WHERE {where_clause}) AS yuan_shi_lianbiao'


def read_source_data(spark_session, scope_id):
    options = mysql_jdbc_options()
    return (
        spark_session.read.format('jdbc')
        .option('url', options['url']).option('driver', options['driver'])
        .option('dbtable', build_raw_mysql_query(scope_id))
        .option('user', options['user']).option('password', options['password']).load()
    )


def select_target_columns(df):
    selected = []
    for column in METADATA_COLUMNS:
        if column == 'yuan_shi_gangwei_bianhao':
            expression = F.col(column).cast('long') if column in df.columns else F.lit(None).cast('long')
        else:
            expression = F.trim(F.coalesce(F.col(column).cast('string'), F.lit(''))) if column in df.columns else F.lit('')
        selected.append(expression.alias(column))
    for column in TARGET_COLUMNS:
        expression = F.trim(F.coalesce(F.col(column).cast('string'), F.lit(''))) if column in df.columns else F.lit('')
        selected.append(expression.alias(column))
    return df.select(*selected)


def map_stage(spark_session, scope_id):
    print('读取关键词:', scope_id)
    source_df = read_source_data(spark_session, scope_id)
    mapped_df = select_target_columns(source_df)
    print('Map输出记录数:', mapped_df.count())
    return mapped_df


# 4. Spark 清洗数据
def format_wan_column(column):
    formatted = F.regexp_replace(F.format_string('%.2f', column), '0+$', '')
    return F.regexp_replace(formatted, '\\.$', '')


def extract_salary_months(salary_col):
    month_text = F.regexp_extract(salary_col, r'(\d+(?:\.\d+)?)\s*薪', 1)
    return F.when(month_text != '', month_text.cast('double')).otherwise(F.lit(float(DEFAULT_MONTHS)))


def extract_salary_bounds(salary_body_col):
    first_number = F.regexp_extract(salary_body_col, r'(\d+(?:\.\d+)?)', 1)
    second_number = F.regexp_extract(salary_body_col, r'\d+(?:\.\d+)?\D+(\d+(?:\.\d+)?)', 1)
    first_value = F.when(first_number != '', first_number.cast('double'))
    second_value = F.when(second_number != '', second_number.cast('double')).otherwise(first_value)
    return F.least(first_value, second_value), F.greatest(first_value, second_value)


def convert_salary_bounds_to_annual(salary_body_col, low_col, high_col, months_col):
    is_day = salary_body_col.contains('元/天') | salary_body_col.contains('/天')
    is_hour = salary_body_col.contains('元/时') | salary_body_col.contains('/时') | salary_body_col.contains('元/小时') | salary_body_col.contains('/小时')
    is_k = salary_body_col.rlike('[kK]')
    is_wan = salary_body_col.contains('万')
    is_qian = salary_body_col.contains('千')
    is_yuan = salary_body_col.contains('元') | (F.greatest(low_col, high_col) >= F.lit(1000.0))
    day_factor = F.lit(float(WORK_DAYS_PER_MONTH * 12 / 10000))
    hour_factor = F.lit(float(HOURS_PER_DAY * WORK_DAYS_PER_MONTH * 12 / 10000))

    def convert(value):
        return (
            F.when(value.isNull(), F.lit(None).cast('double'))
            .when(is_day, value * day_factor).when(is_hour, value * hour_factor)
            .when(is_k, value * months_col / F.lit(10.0)).when(is_wan, value * months_col)
            .when(is_qian, value * F.lit(0.1) * months_col)
            .when(is_yuan, value * months_col / F.lit(10000.0)).otherwise(value * months_col)
        )
    return convert(low_col), convert(high_col)


def build_salary_value_column(annual_col, fill_salary):
    fill_text = '' if fill_salary is None else f'{float(fill_salary):.2f}'.rstrip('0').rstrip('.') + '万'
    return F.when(annual_col.isNull(), F.lit(fill_text)).otherwise(F.concat(format_wan_column(annual_col), F.lit('万')))


def clean_publish_date_column(date_col):
    raw = F.trim(F.coalesce(date_col.cast('string'), F.lit('')))
    year = F.regexp_extract(raw, r'(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})', 1)
    month = F.regexp_extract(raw, r'(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})', 2)
    day = F.regexp_extract(raw, r'(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})', 3)
    return F.when(year != '', F.concat(year, F.lit('-'), F.lpad(month, 2, '0'), F.lit('-'), F.lpad(day, 2, '0'))).otherwise(raw)


def reduce_stage(mapped_df):
    raw_salary = F.trim(F.coalesce(F.col('xinzi').cast('string'), F.lit('')))
    normalized = F.regexp_replace(raw_salary, '[－—–~～至]', '-')
    salary_body = F.regexp_replace(normalized, r'[·・\s]*\d+(?:\.\d+)?\s*薪.*$', '')
    months = extract_salary_months(normalized)
    low, high = extract_salary_bounds(salary_body)
    annual_low, annual_high = convert_salary_bounds_to_annual(salary_body, low, high, months)
    df = mapped_df.withColumn('_annual_low', annual_low).withColumn('_annual_high', annual_high)
    df = df.withColumn('_salary_average', (F.col('_annual_low') + F.col('_annual_high')) / F.lit(2.0))
    average_row = df.select(F.avg('_salary_average').alias('average_salary')).first()
    average_salary = average_row['average_salary'] if average_row else None
    df = (
        df.withColumn('zuidi_xinzi', build_salary_value_column(F.col('_annual_low'), average_salary))
        .withColumn('zuigao_xinzi', build_salary_value_column(F.col('_annual_high'), average_salary))
        .drop('xinzi', '_annual_low', '_annual_high', '_salary_average')
    )
    df = df.withColumn('fabu_shijian', clean_publish_date_column(F.col('fabu_shijian')))
    df = df.drop(*[column for column in DROP_COLUMNS if column in df.columns])
    for column in METADATA_COLUMNS + FINAL_COLUMNS:
        if column not in df.columns:
            data_type = 'long' if column == 'yuan_shi_gangwei_bianhao' else 'string'
            df = df.withColumn(column, F.lit(None).cast(data_type) if data_type == 'long' else F.lit(''))
    return df.select(*CLEAN_JOB_COLUMNS)


# 5. 按关键词替换 MySQL 和 HDFS 清洗快照
def make_mysql_engine():
    password = quote_plus(MYSQL_PASSWORD)
    url = f'mysql+pymysql://{MYSQL_USER}:{password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4'
    return create_engine(url, pool_pre_ping=True)


def stable_hash(*values):
    parts = ['' if pd.isna(value) else str(value).strip() for value in values]
    return hashlib.md5('|'.join(parts).encode('utf-8')).hexdigest()


def build_clean_company_pdf(job_pdf):
    frame = job_pdf.copy()
    frame['gongsi_weiyi_biaoshi'] = frame.apply(
        lambda row: stable_hash(row['guanjianci_biaoshi'], row['laiyuan_chengshi'], row['gongsi_mingcheng']), axis=1
    )
    return frame[CLEAN_COMPANY_COLUMNS].drop_duplicates(
        subset=['guanjianci_biaoshi', 'laiyuan_chengshi', 'gongsi_mingcheng']
    )


def build_clean_recruiter_pdf(job_pdf):
    frame = job_pdf.copy()
    frame['zhaopin_fuzeren_weiyi_biaoshi'] = frame.apply(
        lambda row: stable_hash(
            row['gangwei_weiyi_biaoshi'], row['zhaopin_fuzeren_zhuangtai'],
            row['zhaopin_fuzeren_huoyue_biaoqian']
        ), axis=1
    )
    return frame[CLEAN_RECRUITER_COLUMNS].drop_duplicates(
        subset=['gangwei_weiyi_biaoshi', 'zhaopin_fuzeren_weiyi_biaoshi']
    )


def replace_clean_snapshot(cleaned_df, hdfs_output_file, start_time, end_time):
    job_pdf = cleaned_df.toPandas()
    if job_pdf.empty:
        raise ValueError('清洗结果为空，不能替换清洗快照。')
    company_pdf = build_clean_company_pdf(job_pdf)
    recruiter_pdf = build_clean_recruiter_pdf(job_pdf)
    first = job_pdf.iloc[0]
    scope_id = first['guanjianci_biaoshi']
    engine = make_mysql_engine()

    with engine.begin() as connection:
        params = {'scope_id': scope_id}
        for table in [CLEAN_JOB_TABLE, CLEAN_COMPANY_TABLE, CLEAN_RECRUITER_TABLE]:
            connection.execute(text(f'DELETE FROM {table} WHERE guanjianci_biaoshi = :scope_id'), params)
        job_pdf.to_sql(CLEAN_JOB_TABLE, con=connection, if_exists='append', index=False, chunksize=300, method='multi')
        company_pdf.to_sql(CLEAN_COMPANY_TABLE, con=connection, if_exists='append', index=False, chunksize=300, method='multi')
        recruiter_pdf.to_sql(CLEAN_RECRUITER_TABLE, con=connection, if_exists='append', index=False, chunksize=300, method='multi')
        connection.execute(text(f'''
            INSERT INTO {CLEAN_LOG_TABLE}
            (guanjianci_biaoshi, yunxing_biaoshi, guanjianci, guanjianci_daima,
             chengshi_liebiao, chengshi_daima_liebiao, gangwei_jilu_shuliang,
             gongsi_jilu_shuliang, zhaopin_fuzeren_jilu_shuliang, shuchu_lujing,
             yunxing_zhuangtai, yunxing_shuoming, kaishi_shijian, jieshu_shijian)
            VALUES
            (:scope_id, :run_id, :keyword, :keyword_code, :cities, :city_codes,
             :job_count, :company_count, :recruiter_count, :output_path,
             'success', '清洗成功并替换同一关键词快照', :start_time, :end_time)
            ON DUPLICATE KEY UPDATE
             yunxing_biaoshi=VALUES(yunxing_biaoshi), guanjianci=VALUES(guanjianci),
             guanjianci_daima=VALUES(guanjianci_daima), chengshi_liebiao=VALUES(chengshi_liebiao),
             chengshi_daima_liebiao=VALUES(chengshi_daima_liebiao),
             gangwei_jilu_shuliang=VALUES(gangwei_jilu_shuliang),
             gongsi_jilu_shuliang=VALUES(gongsi_jilu_shuliang),
             zhaopin_fuzeren_jilu_shuliang=VALUES(zhaopin_fuzeren_jilu_shuliang),
             shuchu_lujing=VALUES(shuchu_lujing), yunxing_zhuangtai=VALUES(yunxing_zhuangtai),
             yunxing_shuoming=VALUES(yunxing_shuoming), kaishi_shijian=VALUES(kaishi_shijian),
             jieshu_shijian=VALUES(jieshu_shijian)
        '''), {
            'scope_id': scope_id, 'run_id': first['yunxing_biaoshi'],
            'keyword': first['guanjianci'], 'keyword_code': first['guanjianci_daima'],
            'cities': first['chengshi_liebiao'], 'city_codes': first['chengshi_daima_liebiao'],
            'job_count': len(job_pdf), 'company_count': len(company_pdf),
            'recruiter_count': len(recruiter_pdf), 'output_path': hdfs_output_file,
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
        })

    return {'gangwei_jilu_shuliang': len(job_pdf), 'gongsi_jilu_shuliang': len(company_pdf), 'zhaopin_fuzeren_jilu_shuliang': len(recruiter_pdf)}


def find_hdfs_command():
    command = shutil.which('hdfs') or shutil.which('hdfs.cmd')
    if command is None:
        raise FileNotFoundError('没有找到 hdfs 命令。')
    return command


HDFS_COMMAND = find_hdfs_command()


def get_hdfs_filesystem(spark_session):
    configuration = spark_session._jsc.hadoopConfiguration()
    filesystem = spark_session._jvm.org.apache.hadoop.fs.FileSystem.get(configuration)
    path_class = spark_session._jvm.org.apache.hadoop.fs.Path
    return filesystem, path_class


def find_part_csv_file(filesystem, path_class, temp_output_dir):
    for status in filesystem.listStatus(path_class(temp_output_dir)):
        name = status.getPath().getName()
        if name.startswith('part-') and name.endswith('.csv'):
            return status.getPath()
    raise FileNotFoundError(f'没有找到 part CSV: {temp_output_dir}')


def copy_part_file(part_file, output_file):
    filesystem, path_class = get_hdfs_filesystem(spark)
    src_path = path_class(str(part_file))
    dst_path = path_class(output_file)
    filesystem.delete(dst_path, False)
    filesystem.mkdirs(dst_path.getParent())
    copied = spark._jvm.org.apache.hadoop.fs.FileUtil.copy(
        filesystem,
        src_path,
        filesystem,
        dst_path,
        False,
        spark._jsc.hadoopConfiguration(),
    )
    if not copied:
        raise RuntimeError(f'HDFS复制失败: {src_path} -> {dst_path}')


def write_to_hdfs(cleaned_df, scope_id):
    scope_dir = f'{HDFS_CLEAN_BASE_DIR}/{scope_id}'
    temp_dir = f'{scope_dir}/_linshi_qingxi'
    hive_temp_dir = f'{scope_dir}/_linshi_hive_fenqu'
    output_file = f'{scope_dir}/qingxi_gangwei.csv'
    hive_partition_dir = f'{HDFS_HIVE_INPUT_DIR}/guanjianci_daima={scope_id}'
    hive_input_file = f'{hive_partition_dir}/qingxi_gangwei.csv'
    filesystem, path_class = get_hdfs_filesystem(spark)
    filesystem.delete(path_class(temp_dir), True)
    filesystem.delete(path_class(hive_temp_dir), True)
    filesystem.delete(path_class(output_file), False)
    filesystem.delete(path_class(hive_partition_dir), True)
    filesystem.mkdirs(path_class(scope_dir))
    filesystem.mkdirs(path_class(hive_partition_dir))

    hdfs_df = cleaned_df
    for column_name, data_type in cleaned_df.dtypes:
        if data_type == 'string':
            hdfs_df = hdfs_df.withColumn(column_name, F.regexp_replace(F.col(column_name), r'[\r\n]+', ' '))
    hdfs_df.coalesce(1).write.mode('overwrite').option('header', True).option('encoding', 'UTF-8').csv(temp_dir)
    part_file = find_part_csv_file(filesystem, path_class, temp_dir)
    copy_part_file(part_file, output_file)

    hive_df = hdfs_df.drop(*HIVE_PARTITION_COLUMNS)
    hive_df.coalesce(1).write.mode('overwrite').option('header', True).option('encoding', 'UTF-8').csv(hive_temp_dir)
    hive_part_file = find_part_csv_file(filesystem, path_class, hive_temp_dir)
    copy_part_file(hive_part_file, hive_input_file)
    filesystem.delete(path_class(temp_dir), True)
    filesystem.delete(path_class(hive_temp_dir), True)
    print('清洗输出文件:', output_file)
    print('Hive输入文件:', hive_input_file)
    return output_file


# 6. 总调用
def run_spark_cleaning(scope=SCOPE):
    start_time = datetime.now()
    scope_id = scope['guanjianci_biaoshi']
    mapped_df = map_stage(spark, scope_id)
    cleaned_df = reduce_stage(mapped_df).cache()
    record_count = cleaned_df.count()
    if record_count == 0:
        raise ValueError(f'MySQL原始表没有该关键词的数据: {scope_id}')

    hdfs_output_file = write_to_hdfs(cleaned_df, scope_id)
    end_time = datetime.now()
    mysql_result = replace_clean_snapshot(cleaned_df, hdfs_output_file, start_time, end_time)

    print('清洗完成，关键词:', scope_id)
    print('岗位记录数:', mysql_result['gangwei_jilu_shuliang'])
    print('公司记录数:', mysql_result['gongsi_jilu_shuliang'])
    print('招聘负责人记录数:', mysql_result['zhaopin_fuzeren_jilu_shuliang'])
    print('说明: MySQL、HDFS 和 Hive 输入文件均按关键词保留单快照，城市列表固定统一。')
    return hdfs_output_file, cleaned_df


HDFS_OUTPUT_FILE, result_df = run_spark_cleaning()
result_df.show(5, truncate=False)
