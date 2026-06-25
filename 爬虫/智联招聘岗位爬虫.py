#!/usr/bin/env python
# coding: utf-8

# 说明：requests 负责请求智联前端 JSON 接口，pandas 负责表格处理，SQLAlchemy 负责写入 MySQL。

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import hashlib
import json
import os
import random
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlencode

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from sqlalchemy import create_engine, text
from tqdm.auto import tqdm


# 自定义搜索参数
# 配置关键词、关键词拼音代码和城市列表。关键词由“关键词＋排序去重后的城市代码集合”确定。
# 同一关键词只有一份业务快照；只有统一城市列表全部采集成功时才会事务性替换旧快照。
# 同一关键词生成同一个关键词标识；统一城市列表只作为采集城市清单。

KEYWORD = '数据开发'
KEYWORD_PATH_CODE = 'shuju_kaifa'

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

CITY = CITY_LIST[0]
CITY_CODE = None
START_PAGE = 1
MAX_PAGES = 5
PAGE_SIZE = 20
EMPTY_PAGE_STOP = 2
PAGE_SLEEP_RANGE = (0.4, 1.0)
MAX_CITY_WORKERS = 8
REQUEST_TIMEOUT = 25
REQUEST_RETRIES = 4
RETRY_BACKOFF_BASE = 1.0
RETRY_SLEEP_RANGE = (0.3, 1.0)

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
CRAWLER_LOG_TABLE = 'pachong_yunxing_rizhi'


def locate_project_root():
    cwd = Path.cwd().resolve()
    for base in [cwd, *cwd.parents]:
        if (base / '爬虫').is_dir() and (base / '数据清洗上传HDFS').is_dir():
            return base
    raise FileNotFoundError('没有找到项目根目录。')


PROJECT_ROOT = locate_project_root()

# 城市名称和代码均于 2026-06-22 从智联招聘 citymap 官方页面核对。
CITY_CODE_MAP = {
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

EXTRA_PARAMS = {'order': 4}


# 请求头与安全验证检测
# 智联搜索页 HTML 当前容易返回安全验证页。本脚本改为请求前端 JSON 接口，并保留安全验证检测，避免把验证页误当成岗位数据。
# 说明：搜索页 HTML 现在经常返回安全验证；这里改为请求智联前端 JSON 接口。

SEARCH_API_URL = 'https://fe-api.zhaopin.com/c/i/search/positions'  # 智联岗位搜索 JSON 接口地址

# 请求头参数：模拟浏览器前端接口请求，降低被接口拒绝的概率。
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Content-Type': 'application/json;charset=UTF-8',
    'Origin': 'https://www.zhaopin.com',
    'Referer': 'https://www.zhaopin.com/',
    'Connection': 'keep-alive',
    'x-zp-page-code': '4019',
    'x-zp-platform': '13',
    'x-zp-business-system': '1',
}

# 安全验证特征：响应内容命中这些文本时，说明可能被网站验证拦截。
SECURITY_MARKERS = (
    'Security Verification',
    'TencentEOCaptcha',
    'EO-Bot-Captcha-Token',
    '正在验证连接安全性',
    'Protected by Tencent Cloud EdgeOne',
)


def make_request_session() -> requests.Session:
    """
    Input:
    - 无。
    Output:
    - requests.Session，会话对象。
    Function:
    - 创建带请求头和连接池的 requests 会话。
    """
    new_session = requests.Session()
    new_session.headers.update(HEADERS)
    worker_count = max(1, int(globals().get('MAX_CITY_WORKERS', 1)))
    pool_size = max(8, worker_count * 4)
    adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size, max_retries=0)
    new_session.mount('https://', adapter)
    new_session.mount('http://', adapter)
    return new_session


session = make_request_session()


def reset_request_session() -> None:
    """
    Input:
    - 无。
    Output:
    - None。
    Function:
    - 关闭旧会话并重建请求会话。
    """
    global session
    try:
        session.close()
    except Exception:
        pass
    session = make_request_session()


def looks_like_security_verification(text: str) -> bool:
    """
    Input:
    - text: 需要判断、清理或解析的文本。
    Output:
    - bool，是否命中安全验证特征。
    Function:
    - 判断响应内容是否像安全验证页面。
    """
    return any(marker in text for marker in SECURITY_MARKERS)


# 城市代码、展示 URL 与接口请求体构造
# `build_search_page_url` 用于记录和 Referer；真正取数的是 `build_search_payload` 构造出的 JSON 请求体。
# 说明：build_search_page_url 只用于记录和 Referer；真正取数用 build_search_payload。


def resolve_city_code(city: str, city_code: Optional[str] = None) -> str:
    """
    Input:
    - city: 搜索城市名称。
    - city_code: 智联城市代码；为空时从城市映射表查找。
    Output:
    - str，城市代码。
    Function:
    - 确定接口请求使用的城市代码。
    """
    if city_code not in (None, ''):
        return str(city_code)
    if city in CITY_CODE_MAP:
        return CITY_CODE_MAP[city]
    raise ValueError(f'城市 {city!r} 不在 CITY_CODE_MAP 中，请手动设置 CITY_CODE。')


def build_search_page_url(
    keyword: str,
    city_code: str,
    page: int,
    extra_params: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Input:
    - keyword: 搜索关键词，也是关键词组成部分。
    - city_code: 智联城市代码；为空时从城市映射表查找。
    - page: 请求页码。
    - extra_params: 额外接口筛选参数。
    Output:
    - str，搜索页 URL。
    Function:
    - 构造用于日志和 Referer 的搜索页 URL。
    """
    params = {'kw': keyword, 'p': str(page)}
    if city_code:
        params['jl'] = str(city_code)
    if extra_params:
        for key, value in extra_params.items():
            if value not in (None, '') and key not in {'S_SOU_FULL_INDEX', 'S_SOU_WORK_CITY', 'pageIndex', 'pageSize'}:
                params[key] = value
    return 'https://www.zhaopin.com/sou/?' + urlencode(params)


def build_api_query_params() -> Dict[str, str]:
    """
    Input:
    - 无。
    Output:
    - dict，请求参数。
    Function:
    - 构造接口 URL 上的动态请求参数。
    """
    return {
        '_v': f'{random.random():.8f}',
        'x-zp-page-request-id': f'{int(time.time() * 1000)}-{random.randint(100000, 999999)}',
        'x-zp-client-id': str(uuid.uuid4()),
    }


def build_search_payload(
    keyword: str,
    city_code: str,
    page: int,
    page_size: int = 20,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Input:
    - keyword: 搜索关键词，也是关键词组成部分。
    - city_code: 智联城市代码；为空时从城市映射表查找。
    - page: 请求页码。
    - page_size: 每页岗位数量。
    - extra_params: 额外接口筛选参数。
    Output:
    - dict，请求体。
    Function:
    - 构造智联岗位搜索 JSON 请求体。
    """
    payload: Dict[str, Any] = {
        'S_SOU_FULL_INDEX': keyword,
        'pageIndex': int(page),
        'pageSize': int(page_size),
        'anonymous': 1,
        'eventScenario': 'pcSearchedSouSearch',
        'platform': 13,
        'version': '0.0.0',
        'order': 4,
    }
    if city_code:
        payload['S_SOU_WORK_CITY'] = str(city_code)
    if extra_params:
        payload.update({k: v for k, v in extra_params.items() if v not in (None, '')})
    return payload


# 先打印一个示例 URL 和请求体，确认关键词和城市参数是否正确。
resolved_city_code = resolve_city_code(CITY, CITY_CODE)
example_url = build_search_page_url(KEYWORD, resolved_city_code, START_PAGE, EXTRA_PARAMS)
example_payload = build_search_payload(KEYWORD, resolved_city_code, START_PAGE, PAGE_SIZE, EXTRA_PARAMS)
print(example_url)
print(json.dumps(example_payload, ensure_ascii=False, indent=2))


# JSON 接口请求函数
# 这一格请求 `https://fe-api.zhaopin.com/c/i/search/positions`，并检查是否返回安全验证或异常 JSON。
# 说明：搜索页 HTML 会被安全验证拦截；这里直接请求前端 JSON 接口并返回 data。

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}  # 这些 HTTP 状态码会触发重试
RETRYABLE_REQUEST_EXCEPTIONS = (  # 这些网络异常会触发重试

    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


class PageRequestError(RuntimeError):
    """单页接口请求多次重试后仍失败。"""


def retry_wait_seconds(attempt: int) -> float:
    """
    Input:
    - attempt: 当前重试次数，从 1 开始。
    Output:
    - float，等待秒数。
    Function:
    - 计算重试等待时间。
    """
    base = RETRY_BACKOFF_BASE * (2 ** max(attempt - 1, 0))
    jitter = random.uniform(*RETRY_SLEEP_RANGE)
    return min(base + jitter, 30.0)


def fetch_position_page(
    keyword: str,
    city_code: str,
    page: int,
    page_size: int = 20,
    extra_params: Optional[Dict[str, Any]] = None,
    timeout: int = 25,
    retries: Optional[int] = None,
    request_session: Optional[requests.Session] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    Input:
    - keyword: 搜索关键词，也是关键词组成部分。
    - city_code: 智联城市代码；为空时从城市映射表查找。
    - page: 请求页码。
    - page_size: 每页岗位数量。
    - extra_params: 额外接口筛选参数。
    - timeout: 单次请求超时时间，单位秒。
    - retries: 最大重试次数；为空时使用全局默认值。
    - request_session: requests 会话对象；为空时使用全局会话。
    Output:
    - tuple，接口 data、请求 payload、请求 URL。
    Function:
    - 请求一页岗位 JSON，并处理重试和安全验证。
    """
    payload = build_search_payload(keyword, city_code, page, page_size, extra_params)
    page_url = build_search_page_url(keyword, city_code, page, extra_params)
    headers = dict(HEADERS)
    headers['Referer'] = page_url
    max_retries = REQUEST_RETRIES if retries is None else int(retries)
    last_error: Optional[BaseException] = None
    active_session = request_session or session

    for attempt in range(1, max_retries + 1):
        api_params = build_api_query_params()
        try:
            resp = active_session.post(
                SEARCH_API_URL,
                params=api_params,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                timeout=timeout,
            )

            if resp.status_code in RETRYABLE_STATUS_CODES:
                raise requests.exceptions.HTTPError(
                    f'HTTP {resp.status_code}: {resp.text[:200]!r}',
                    response=resp,
                )

            resp.raise_for_status()
            text = resp.text
            if looks_like_security_verification(text):
                raise RuntimeError('接口返回了网站安全验证页。请降低频率，稍后重试，或在浏览器中完成验证后再运行。')

            try:
                result = resp.json()
            except ValueError as exc:
                raise RuntimeError(f'接口没有返回 JSON，前 300 字符：{text[:300]!r}') from exc

            if result.get('code') != 200 or result.get('apiCode') not in (None, 200):
                raise RuntimeError(f'接口返回异常：{json.dumps(result, ensure_ascii=False)[:500]}')

            data = result.get('data') or {}
            if data.get('isVerification'):
                raise RuntimeError('接口提示需要安全验证，未继续抓取。')
            if not isinstance(data.get('list', []), list):
                raise RuntimeError(f'接口 data.list 不是列表：{json.dumps(data, ensure_ascii=False)[:500]}')

            return data, payload, resp.url

        except RETRYABLE_REQUEST_EXCEPTIONS as exc:
            last_error = exc
            if request_session is None:
                reset_request_session()
                active_session = session
        except requests.exceptions.HTTPError as exc:
            last_error = exc
            response = getattr(exc, 'response', None)
            status_code = getattr(response, 'status_code', None)
            if status_code not in RETRYABLE_STATUS_CODES:
                raise
            if request_session is None:
                reset_request_session()
                active_session = session

        if attempt < max_retries:
            wait_seconds = retry_wait_seconds(attempt)
            print(f'第 {page} 页请求失败，{wait_seconds:.1f} 秒后重试 {attempt}/{max_retries}：{last_error!r}')
            time.sleep(wait_seconds)

    raise PageRequestError(f'第 {page} 页连续 {max_retries} 次请求失败：{last_error!r}') from last_error


# 浏览器备用说明
# 当前版本不再使用 Playwright 抓 HTML。最后保留一个空的关闭函数，用于统一结束流程。
# 说明：当前版本不再依赖 Playwright 解析页面 HTML；保留关闭函数用于统一结束流程。


def close_playwright_browser():
    """
    Input:
    - 无。
    Output:
    - None。
    Function:
    - 保留浏览器关闭入口；当前接口版不启动浏览器。
    """
    return None


# 解析接口返回数据
# 职位列表来自接口返回的 `data.list`，总数来自 `data.count`，是否最后一页来自 `data.isEndPage`。
# 说明：职位列表在接口返回的 data.list 中，count 是接口给出的结果数量，isEndPage 表示是否最后一页。


def extract_position_page_data(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int, bool]:
    """
    Input:
    - data: 接口返回的 data 字典。
    Output:
    - tuple，岗位列表、总数、是否末页。
    Function:
    - 从接口 data 中提取岗位列表、总数和是否末页。
    """
    jobs = data.get('list') or []
    count = int(data.get('count') or 0)
    is_end_page = bool(data.get('isEndPage'))
    return jobs, count, is_end_page


# 基础清洗工具
# 后面整理字段时，会遇到列表、字典、空值、重复标签等情况。这里放通用小函数，避免后面的字段整理代码太乱。
# 说明：这些函数只做文本清洗、路径取值、列表合并，不涉及具体业务字段。


def get_path(obj: Any, path: List[str], default: Any = '') -> Any:
    """
    Input:
    - obj: 需要读取的字典对象。
    - path: 多层字段路径。
    - default: 取值失败时返回的默认值。
    Output:
    - Any，取到的值或默认值。
    Function:
    - 按路径从多层字典中安全取值。
    """
    cur = obj
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return default if cur is None else cur


def clean_text(value: Any) -> str:
    """
    Input:
    - value: 需要清洗、格式化或转义的输入值。
    Output:
    - str，清洗后的文本。
    Function:
    - 清洗文本空白并统一转成字符串。
    """
    if value is None:
        return ''
    if isinstance(value, str):
        return ' '.join(value.split())
    return str(value)


def unique_join(values: List[Any], sep: str = ' | ') -> str:
    """
    Input:
    - values: 参与拼接或签名的一组值。
    - sep: 拼接字符串时使用的分隔符。
    Output:
    - str，拼接后的文本。
    Function:
    - 去空去重后拼接列表文本。
    """
    seen = set()
    result = []
    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return sep.join(result)


def parse_json_field(value: Any) -> Dict[str, Any]:
    """
    Input:
    - value: 需要清洗、格式化或转义的输入值。
    Output:
    - dict，解析结果；失败时为空字典。
    Function:
    - 解析字段中嵌套的 JSON 字符串。
    """
    if not value or not isinstance(value, str):
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


# 标签提取工具
# 岗位标签来源很多：`showSkillTags`、`jobSkillTags`、福利、职位关键词、职位详情里的标签等。这里把这些不同格式统一成文本列表。
# 说明：尽可能把岗位相关标签都保留下来，后面你可以自己筛选需要的列。


def list_values(
    items: Any,
    keys: Tuple[str, ...] = ('name', 'value', 'tag', 'itemValue', 'title', 'text', 'label', 'description'),
) -> List[str]:
    """
    Input:
    - items: 需要提取标签的原始列表、字典或普通值。
    - keys: 从字典中读取标签时尝试的候选字段名。
    Output:
    - list[str]，标签文本列表。
    Function:
    - 从多种标签结构中提取标签文本。
    """
    if not items:
        return []
    if isinstance(items, dict):
        items = [items]
    if isinstance(items, (str, int, float)):
        return [clean_text(items)]

    values = []
    for item in items:
        if isinstance(item, dict):
            for key in keys:
                if item.get(key) not in (None, ''):
                    values.append(item[key])
                    break
        else:
            values.append(item)
    return [clean_text(v) for v in values if clean_text(v)]


def key_value_items(items: Any, name_key: str = 'name', value_key: str = 'value') -> List[str]:
    """
    Input:
    - items: 需要提取标签的原始列表、字典或普通值。
    - name_key: 键值结构中的名称字段名。
    - value_key: 键值结构中的值字段名。
    Output:
    - list[str]，键值标签列表。
    Function:
    - 把 name/value 结构转为可读标签。
    """
    if not items:
        return []

    values = []
    for item in items:
        if not isinstance(item, dict):
            values.append(clean_text(item))
            continue

        name = clean_text(item.get(name_key, ''))
        value = clean_text(item.get(value_key, ''))
        if name and value and name != value:
            values.append(f'{name}:{value}')
        elif name:
            values.append(name)
        elif value:
            values.append(value)
    return values


def collect_all_tags(job: Dict[str, Any]) -> str:
    """
    Input:
    - job: 单条岗位原始 JSON。
    Output:
    - str，标签汇总文本。
    Function:
    - 汇总单个岗位中的所有标签。
    """
    jd = job.get('jobDetailData') or {}
    custom = jd.get('customAttributeInfo') or {}
    desc = get_path(jd, ['position', 'desc'], {})

    tags = []
    tags += list_values(job.get('jobSkillTags'), ('name', 'value', 'tag'))
    tags += list_values(job.get('skillLabel'), ('value', 'name', 'tag'))
    tags += list_values(job.get('showSkillTags'), ('tag', 'name', 'value'))
    tags += list_values(get_path(job, ['jobKeyword', 'keywords'], []), ('itemValue', 'name', 'tag', 'value'))
    tags += list_values(desc.get('labels'))
    tags += list_values(desc.get('welfareLabel'))
    tags += list_values(desc.get('welfareTags'))
    tags += list_values(job.get('welfareLabel'))
    tags += list_values(custom.get('reportItems'))
    tags += key_value_items(custom.get('welfareItems'))
    tags += key_value_items(custom.get('workTimeItems'))
    tags += list_values(job.get('searchTagList'))
    tags += list_values(job.get('commercialLabel'))
    tags += list_values(job.get('orgCommercialTags'))
    tags += list_values(job.get('companyScaleTypeTagsNew'))

    if job.get('tagABC'):
        tags.append(job.get('tagABC'))
    return unique_join(tags)


# 把单个岗位整理成一行
# 所有进入 MySQL、HDFS 和 Hive 的字段都使用小写全拼加下划线命名。
def flatten_job(job: Dict[str, Any], page: int, keyword: str, city: str, city_code: str) -> Dict[str, Any]:
    jd = job.get('jobDetailData') or {}
    pos = jd.get('position') or {}
    base = pos.get('base') or {}
    desc = pos.get('desc') or {}
    custom = jd.get('customAttributeInfo') or {}
    workloc = jd.get('workLocation') or {}
    staff_detail = jd.get('staff') or {}
    staff_card = job.get('staffCard') or {}
    state = get_path(jd, ['stateInfo', 'state'], {})
    verify_basic = get_path(jd, ['verifyTheTruth', 'basic'], {})
    card = parse_json_field(job.get('cardCustomJson'))

    skill_tags = []
    skill_tags += list_values(job.get('jobSkillTags'), ('name',))
    skill_tags += list_values(job.get('skillLabel'), ('value', 'name'))
    skill_tags += list_values(job.get('showSkillTags'), ('tag', 'name', 'value'))

    welfare_tags = []
    welfare_tags += list_values(desc.get('welfareLabel'))
    welfare_tags += list_values(desc.get('welfareTags'))
    welfare_tags += list_values(job.get('welfareLabel'))
    welfare_tags += key_value_items(custom.get('welfareItems'))

    return {
        'guanjianci': keyword,
        'laiyuan_chengshi': city,
        'chengshi_daima': city_code,
        'yema': page,
        'zhiwei_bianhao': job.get('jobId') or base.get('positionId'),
        'zhiwei_xuhao': job.get('number') or base.get('positionNumber'),
        'zhiwei_mingcheng': job.get('name') or base.get('positionName'),
        'zhiwei_lianjie': job.get('positionURL') or job.get('positionUrl') or base.get('positionUrl'),
        'xinzi': job.get('salary60') or base.get('salary') or card.get('salary60'),
        'xinzi_yuanshi_qujian': job.get('salaryReal') or base.get('salaryReal'),
        'xinzi_leixing': job.get('salaryType', ''),
        'xinzi_fafang_cishu': job.get('salaryCount', ''),
        'gongzuo_chengshi': job.get('workCity') or workloc.get('positionWorkCity'),
        'xingzhengqu': job.get('cityDistrict') or workloc.get('positionCityDistrict'),
        'shangquan_jiedao': unique_join([job.get('tradingArea'), job.get('streetName'), workloc.get('tradingArea'), workloc.get('streetName')]),
        'gongzuo_didian': workloc.get('address') or card.get('address') or job.get('workCity'),
        'xiangxi_dizhi': workloc.get('workAddress', ''),
        'jingdu': workloc.get('longitude', ''),
        'weidu': workloc.get('latitude', ''),
        'jingyan_yaoqiu': job.get('workingExp') or base.get('positionWorkingExp'),
        'xueli_yaoqiu': job.get('education') or base.get('education'),
        'gongzuo_leixing': job.get('workType') or base.get('workType'),
        'gongzuo_moshi': job.get('workMode') or state.get('workModeDesc') or state.get('workMode'),
        'zhiwei_leibie': unique_join([
            job.get('jobTypeLevelName'), job.get('subJobTypeLevelName'),
            get_path(jd, ['jobType', 'jobTypeLevelName']),
            get_path(jd, ['jobType', 'subJobTypeLevelName']),
        ]),
        'gongsi_mingcheng': job.get('companyName') or card.get('companyName'),
        'gongsi_bianhao': job.get('companyNumber'),
        'gongsi_lianjie': job.get('companyUrl'),
        'gongsi_tubiao_lianjie': job.get('companyLogo'),
        'gongsi_guimo': job.get('companySize'),
        'gongsi_xingzhi': job.get('propertyName') or job.get('property'),
        'rongzi_jieduan': job.get('financingStage') or card.get('strengthLabel'),
        'hangye': job.get('industryName'),
        'fabu_shijian': job.get('publishTime') or get_path(pos, ['date', 'positionPublishTime']) or get_path(pos, ['date', 'positionUpdateTimeText']),
        'shouci_fabu_shijian': job.get('firstPublishTime') or get_path(pos, ['date', 'firstPublishTime']),
        'fabu_riqi_wenben': get_path(pos, ['date', 'positionUpdateTimeText']),
        'shifou_xin_zhiwei': job.get('isNewPosition'),
        'zhaopin_renshu': job.get('recruitNumber') or base.get('recruitNumber'),
        'zhaopin_fuzeren_xingming': staff_card.get('staffName') or staff_detail.get('staffName'),
        'zhaopin_fuzeren_zhiwei': staff_card.get('hrJob') or staff_detail.get('hrJob'),
        'zhaopin_fuzeren_zhuangtai': staff_card.get('hrStateInfo') or staff_detail.get('hrStateInfo'),
        'zhaopin_fuzeren_huoyue_biaoqian': unique_join(staff_detail.get('activityLevel') or []),
        'zhiwei_biaoqian_huizong': collect_all_tags(job),
        'jineng_biaoqian': unique_join(skill_tags),
        'sousuo_mingzhong_guanjianci': unique_join(list_values(get_path(job, ['jobKeyword', 'keywords'], []), ('itemValue', 'name', 'value'))),
        'fuli_biaoqian': unique_join(welfare_tags),
        'fuli_mingxi': unique_join(key_value_items(custom.get('welfareItems'))),
        'gongzuo_shijian': unique_join(key_value_items(custom.get('workTimeItems'))),
        'baogao_baozhang_xiang': unique_join(list_values(custom.get('reportItems'))),
        'zhiwei_miaoshu': desc.get('description') or get_path(pos, ['desc', 'description']),
        'zhiwei_liangdian': desc.get('descriptionHighlight') or job.get('positionHighlight'),
        'zhiwei_zhaiyao': job.get('jobSummary', ''),
        'renzheng_shouhu_xinxi': verify_basic.get('description') or get_path(jd, ['secure', 'safeCenter', 'title']),
        'yuanshi_neirong': json.dumps(job, ensure_ascii=False),
    }


# 主爬取函数
# 本段逻辑负责翻页、请求 JSON 接口、解析职位列表，并返回三个 DataFrame：`clean_df` 是最终导出的整理字段；`raw_df` 和 `meta_df` 只用于检查原始字段和每页抓取情况，不会在入库步骤里保存成文件。
# 返回值说明：clean_df 是最终导出的整理表；raw_df 和 meta_df 只用于检查字段和页码抓取情况，不再导出文件。


def crawl_zhaopin(
    keyword: str,
    city: str,
    city_code: Optional[str] = None,
    start_page: int = 1,
    max_pages: int = 1,
    page_size: int = 20,
    extra_params: Optional[Dict[str, Any]] = None,
    empty_page_stop: int = 2,
    show_page_progress: bool = True,
):
    """
    Input:
    - keyword: 搜索关键词，也是关键词组成部分。
    - city: 搜索城市名称。
    - city_code: 智联城市代码；为空时从城市映射表查找。
    - start_page: 开始抓取的页码。
    - max_pages: 最多抓取页数。
    - page_size: 每页岗位数量。
    - extra_params: 额外接口筛选参数。
    - empty_page_stop: 连续空页达到该数量后停止当前城市。
    - show_page_progress: 是否显示单城市页码进度条。
    Output:
    - tuple，clean_df、raw_df、meta_df。
    Function:
    - 按关键词、城市和页码范围抓取岗位数据。
    """
    resolved_city_code = resolve_city_code(city, city_code)
    all_jobs = []
    meta_rows = []
    stop_page = start_page + max_pages - 1
    empty_page_count = 0
    request_session = make_request_session()

    try:
        page_range = range(start_page, stop_page + 1)
        if show_page_progress:
            page_range = tqdm(page_range, desc=f'{city}页码', leave=False)

        for page_no in page_range:
            page_url = build_search_page_url(keyword, resolved_city_code, page_no, extra_params=extra_params)
            print(f'[{city}] 抓取第 {page_no} 页：{page_url}')

            try:
                data, payload, api_url = fetch_position_page(
                    keyword=keyword,
                    city_code=resolved_city_code,
                    page=page_no,
                    page_size=page_size,
                    extra_params=extra_params,
                    timeout=REQUEST_TIMEOUT,
                    request_session=request_session,
                )
            except PageRequestError as exc:
                failed_payload = build_search_payload(keyword, resolved_city_code, page_no, page_size, extra_params)
                meta_rows.append({
                    'page': page_no,
                    'url': page_url,
                    'api_url': SEARCH_API_URL,
                    'jobs': 0,
                    'reported_pages': '',
                    'position_count': '',
                    'is_end_page': '',
                    'is_verification': '',
                    'task_id': '',
                    'error': repr(exc),
                    'request_payload': json.dumps(failed_payload, ensure_ascii=False),
                })
                print(f'[{city}] 第 {page_no} 页多次重试仍失败，保留当前城市已抓到的数据并停止该城市：{exc!r}')
                break

            jobs, position_count, is_end_page = extract_position_page_data(data)
            reported_pages = (position_count + page_size - 1) // page_size if position_count else 0

            meta_rows.append({
                'page': page_no,
                'url': page_url,
                'api_url': api_url,
                'jobs': len(jobs),
                'reported_pages': reported_pages,
                'position_count': position_count,
                'is_end_page': int(is_end_page),
                'is_verification': data.get('isVerification', ''),
                'task_id': data.get('taskId', ''),
                'error': '',
                'request_payload': json.dumps(payload, ensure_ascii=False),
            })

            if not jobs:
                empty_page_count += 1
                print(f'[{city}] 当前页没有职位，连续空页数：{empty_page_count}/{empty_page_stop}')
                if empty_page_count >= empty_page_stop:
                    print(f'[{city}] 连续空页达到停止阈值，停止抓取。')
                    break
                if page_no < stop_page:
                    time.sleep(random.uniform(*PAGE_SLEEP_RANGE))
                continue

            empty_page_count = 0
            for job in jobs:
                item = dict(job)
                item['_page'] = page_no
                all_jobs.append(item)

            if is_end_page:
                print(f'[{city}] 接口提示已经到达最后一页。')
                break

            if page_no < stop_page:
                time.sleep(random.uniform(*PAGE_SLEEP_RANGE))
    finally:
        request_session.close()

    clean_rows = [
        flatten_job(job, page=job.get('_page', ''), keyword=keyword, city=city, city_code=resolved_city_code)
        for job in all_jobs
    ]
    clean_df = pd.DataFrame(clean_rows)
    raw_df = pd.json_normalize(all_jobs, sep='.') if all_jobs else pd.DataFrame()
    meta_df = pd.DataFrame(meta_rows)
    return clean_df, raw_df, meta_df


# 执行抓取并自动入库
# 成功条件是固定城市列表内没有失败城市且岗位结果非空。成功时按 `guanjianci_biaoshi` 删除旧快照并写入新快照；失败或部分成功时保留上一次成功数据。
CRAWL_START_TIME = datetime.now()

RAW_JOB_COLUMNS = [
    'yunxing_biaoshi', 'guanjianci', 'guanjianci_daima', 'guanjianci_biaoshi',
    'chengshi_liebiao', 'chengshi_daima_liebiao', 'laiyuan_chengshi', 'chengshi_daima',
    'yema', 'gangwei_weiyi_biaoshi', 'chuangjian_shijian',
    'zhiwei_bianhao', 'zhiwei_xuhao', 'zhiwei_mingcheng', 'zhiwei_lianjie',
    'xinzi', 'xinzi_yuanshi_qujian', 'xinzi_leixing', 'xinzi_fafang_cishu',
    'gongzuo_chengshi', 'xingzhengqu', 'shangquan_jiedao', 'gongzuo_didian',
    'xiangxi_dizhi', 'jingdu', 'weidu', 'jingyan_yaoqiu', 'xueli_yaoqiu',
    'gongzuo_leixing', 'gongzuo_moshi', 'zhiwei_leibie', 'gongsi_mingcheng',
    'fabu_shijian', 'shouci_fabu_shijian', 'fabu_riqi_wenben', 'shifou_xin_zhiwei',
    'zhaopin_renshu', 'zhiwei_biaoqian_huizong', 'sousuo_mingzhong_guanjianci',
    'jineng_biaoqian', 'fuli_biaoqian', 'fuli_mingxi', 'gongzuo_shijian',
    'baogao_baozhang_xiang', 'zhiwei_miaoshu', 'zhiwei_liangdian', 'zhiwei_zhaiyao',
    'renzheng_shouhu_xinxi', 'yuanshi_neirong'
]

RAW_COMPANY_COLUMNS = [
    'yunxing_biaoshi', 'guanjianci', 'guanjianci_daima', 'guanjianci_biaoshi',
    'chengshi_liebiao', 'chengshi_daima_liebiao', 'laiyuan_chengshi',
    'gongsi_weiyi_biaoshi', 'chuangjian_shijian', 'gongsi_mingcheng',
    'gongsi_bianhao', 'gongsi_lianjie', 'gongsi_tubiao_lianjie', 'gongsi_guimo',
    'gongsi_xingzhi', 'rongzi_jieduan', 'hangye'
]

RAW_RECRUITER_COLUMNS = [
    'yunxing_biaoshi', 'guanjianci', 'guanjianci_daima', 'guanjianci_biaoshi',
    'chengshi_liebiao', 'chengshi_daima_liebiao', 'laiyuan_chengshi',
    'gangwei_weiyi_biaoshi', 'zhaopin_fuzeren_weiyi_biaoshi', 'chuangjian_shijian',
    'zhiwei_mingcheng', 'gongsi_mingcheng', 'zhaopin_fuzeren_xingming',
    'zhaopin_fuzeren_zhiwei', 'zhaopin_fuzeren_zhuangtai',
    'zhaopin_fuzeren_huoyue_biaoqian'
]


def make_mysql_engine():
    password = quote_plus(MYSQL_PASSWORD)
    url = f'mysql+pymysql://{MYSQL_USER}:{password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4'
    return create_engine(url, pool_pre_ping=True)


def stable_hash(*values):
    parts = ['' if pd.isna(value) else str(value).strip() for value in values]
    return hashlib.md5('|'.join(parts).encode('utf-8')).hexdigest()


def build_collection_scope(keyword, keyword_code, city_list):
    city_by_code = {}
    for city in city_list:
        code = resolve_city_code(city)
        city_by_code[str(code)] = str(city).strip()
    ordered_pairs = sorted(city_by_code.items(), key=lambda item: item[0])
    city_codes = [item[0] for item in ordered_pairs]
    city_names = [item[1] for item in ordered_pairs]
    return {
        'guanjianci_biaoshi': str(keyword_code).strip(),
        'chengshi_liebiao': ','.join(city_names),
        'chengshi_daima_liebiao': ','.join(city_codes),
        'city_names': city_names,
    }


def make_run_id(scope_id):
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'{stamp}_{scope_id}_{uuid.uuid4().hex[:8]}'


def normalize_db_frame(df, columns):
    frame = df.copy()
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
    return frame[columns].where(pd.notna(frame[columns]), None)


def add_scope_columns(df, scope, run_id, created_at):
    frame = df.copy()
    frame['yunxing_biaoshi'] = run_id
    frame['guanjianci'] = KEYWORD
    frame['guanjianci_daima'] = KEYWORD_PATH_CODE
    frame['guanjianci_biaoshi'] = scope['guanjianci_biaoshi']
    frame['chengshi_liebiao'] = scope['chengshi_liebiao']
    frame['chengshi_daima_liebiao'] = scope['chengshi_daima_liebiao']
    frame['chuangjian_shijian'] = created_at
    return frame


def prepare_raw_job_df(clean_df, scope, run_id, created_at):
    frame = add_scope_columns(clean_df, scope, run_id, created_at)
    frame['yema'] = pd.to_numeric(frame.get('yema'), errors='coerce').astype('Int64').astype(object)
    frame['gangwei_weiyi_biaoshi'] = frame.apply(
        lambda row: stable_hash(
            row.get('zhiwei_bianhao'), row.get('zhiwei_mingcheng'),
            row.get('gongsi_mingcheng'), row.get('gongzuo_didian'), row.get('fabu_shijian')
        ), axis=1
    )
    return normalize_db_frame(frame, RAW_JOB_COLUMNS)


def prepare_raw_company_df(clean_df, scope, run_id, created_at):
    frame = add_scope_columns(clean_df, scope, run_id, created_at)
    frame['gongsi_weiyi_biaoshi'] = frame.apply(
        lambda row: stable_hash(scope['guanjianci_biaoshi'], row.get('laiyuan_chengshi'), row.get('gongsi_mingcheng')),
        axis=1,
    )
    frame = normalize_db_frame(frame, RAW_COMPANY_COLUMNS)
    return frame.drop_duplicates(subset=['guanjianci_biaoshi', 'laiyuan_chengshi', 'gongsi_mingcheng'])


def prepare_raw_recruiter_df(clean_df, scope, run_id, created_at):
    frame = add_scope_columns(clean_df, scope, run_id, created_at)
    frame['gangwei_weiyi_biaoshi'] = frame.apply(
        lambda row: stable_hash(
            row.get('zhiwei_bianhao'), row.get('zhiwei_mingcheng'),
            row.get('gongsi_mingcheng'), row.get('gongzuo_didian'), row.get('fabu_shijian')
        ), axis=1
    )
    frame['zhaopin_fuzeren_weiyi_biaoshi'] = frame.apply(
        lambda row: stable_hash(
            row.get('gangwei_weiyi_biaoshi'), row.get('zhaopin_fuzeren_xingming'),
            row.get('zhaopin_fuzeren_zhiwei'), row.get('zhaopin_fuzeren_zhuangtai'),
            row.get('zhaopin_fuzeren_huoyue_biaoqian')
        ), axis=1
    )
    frame = normalize_db_frame(frame, RAW_RECRUITER_COLUMNS)
    return frame.drop_duplicates(subset=['gangwei_weiyi_biaoshi', 'zhaopin_fuzeren_weiyi_biaoshi'])


def upsert_pachong_log(connection, scope, run_id, status, message, job_count, company_count, recruiter_count, failed_df, start_time, end_time):
    failed_count = 0 if failed_df is None else len(failed_df)
    planned_count = len(scope['city_names'])
    success_count = max(0, planned_count - failed_count)
    statement = text(f'''
        INSERT INTO {CRAWLER_LOG_TABLE}
        (guanjianci_biaoshi, yunxing_biaoshi, guanjianci, guanjianci_daima,
         chengshi_liebiao, chengshi_daima_liebiao, jihua_chengshi_shuliang,
         chenggong_chengshi_shuliang, shibai_chengshi_shuliang,
         gangwei_jilu_shuliang, gongsi_jilu_shuliang, zhaopin_fuzeren_jilu_shuliang,
         yunxing_zhuangtai, yunxing_shuoming, kaishi_shijian, jieshu_shijian)
        VALUES
        (:scope_id, :run_id, :keyword, :keyword_code, :cities, :city_codes,
         :planned_count, :success_count, :failed_count, :job_count, :company_count,
         :recruiter_count, :status, :message, :start_time, :end_time)
        ON DUPLICATE KEY UPDATE
         yunxing_biaoshi=VALUES(yunxing_biaoshi), guanjianci=VALUES(guanjianci),
         guanjianci_daima=VALUES(guanjianci_daima), chengshi_liebiao=VALUES(chengshi_liebiao),
         chengshi_daima_liebiao=VALUES(chengshi_daima_liebiao),
         jihua_chengshi_shuliang=VALUES(jihua_chengshi_shuliang),
         chenggong_chengshi_shuliang=VALUES(chenggong_chengshi_shuliang),
         shibai_chengshi_shuliang=VALUES(shibai_chengshi_shuliang),
         gangwei_jilu_shuliang=VALUES(gangwei_jilu_shuliang),
         gongsi_jilu_shuliang=VALUES(gongsi_jilu_shuliang),
         zhaopin_fuzeren_jilu_shuliang=VALUES(zhaopin_fuzeren_jilu_shuliang),
         yunxing_zhuangtai=VALUES(yunxing_zhuangtai), yunxing_shuoming=VALUES(yunxing_shuoming),
         kaishi_shijian=VALUES(kaishi_shijian), jieshu_shijian=VALUES(jieshu_shijian)
    ''')
    connection.execute(statement, {
        'scope_id': scope['guanjianci_biaoshi'], 'run_id': run_id,
        'keyword': KEYWORD, 'keyword_code': KEYWORD_PATH_CODE,
        'cities': scope['chengshi_liebiao'], 'city_codes': scope['chengshi_daima_liebiao'],
        'planned_count': planned_count, 'success_count': success_count, 'failed_count': failed_count,
        'job_count': int(job_count), 'company_count': int(company_count),
        'recruiter_count': int(recruiter_count), 'status': status, 'message': message[:1000],
        'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
    })


def save_crawl_result_to_mysql(clean_df, scope, summary_df, failed_df, start_time):
    engine = make_mysql_engine()
    end_time = datetime.now()
    run_id = make_run_id(scope['guanjianci_biaoshi'])
    created_at = end_time.strftime('%Y-%m-%d %H:%M:%S')
    failed_count = 0 if failed_df is None else len(failed_df)
    can_replace = not clean_df.empty and failed_count == 0

    if can_replace:
        raw_job_df = prepare_raw_job_df(clean_df, scope, run_id, created_at)
        raw_company_df = prepare_raw_company_df(clean_df, scope, run_id, created_at)
        raw_recruiter_df = prepare_raw_recruiter_df(clean_df, scope, run_id, created_at)
        status = 'success'
        message = '采集成功，已替换同一关键词的原始数据快照'
    else:
        raw_job_df = pd.DataFrame()
        raw_company_df = pd.DataFrame()
        raw_recruiter_df = pd.DataFrame()
        status = 'partial' if not clean_df.empty else 'failed'
        message = '本次采集不完整，未替换该关键词上一次成功数据'

    with engine.begin() as connection:
        if can_replace:
            params = {'scope_id': scope['guanjianci_biaoshi']}
            for table in [RAW_JOB_TABLE, RAW_COMPANY_TABLE, RAW_RECRUITER_TABLE]:
                connection.execute(text(f'DELETE FROM {table} WHERE guanjianci_biaoshi = :scope_id'), params)
            raw_job_df.to_sql(RAW_JOB_TABLE, con=connection, if_exists='append', index=False, chunksize=300, method='multi')
            raw_company_df.to_sql(RAW_COMPANY_TABLE, con=connection, if_exists='append', index=False, chunksize=300, method='multi')
            raw_recruiter_df.to_sql(RAW_RECRUITER_TABLE, con=connection, if_exists='append', index=False, chunksize=300, method='multi')
        upsert_pachong_log(
            connection, scope, run_id, status, message, len(raw_job_df), len(raw_company_df),
            len(raw_recruiter_df), failed_df, start_time, end_time
        )

    return {
        'yunxing_biaoshi': run_id,
        'guanjianci_biaoshi': scope['guanjianci_biaoshi'],
        'gangwei_jilu_shuliang': len(raw_job_df),
        'gongsi_jilu_shuliang': len(raw_company_df),
        'zhaopin_fuzeren_jilu_shuliang': len(raw_recruiter_df),
        'yunxing_zhuangtai': status,
        'shifou_tihuan': can_replace,
    }


SCOPE = build_collection_scope(KEYWORD, KEYWORD_PATH_CODE, CITY_LIST)
ACTIVE_CITY_LIST = SCOPE['city_names']
WORKER_COUNT = min(max(1, int(MAX_CITY_WORKERS)), len(ACTIVE_CITY_LIST)) if ACTIVE_CITY_LIST else 1
city_clean_frames = []
city_summary_rows = []
failed_cities = []


def crawl_city_task(city_index, city_name):
    print(f'\n===== 开始抓取城市：{city_name}，页码 {START_PAGE}-{START_PAGE + MAX_PAGES - 1} =====')
    try:
        current_clean_df, _, current_meta_df = crawl_zhaopin(
            keyword=KEYWORD, city=city_name, city_code=None, start_page=START_PAGE,
            max_pages=MAX_PAGES, page_size=PAGE_SIZE, extra_params=EXTRA_PARAMS,
            empty_page_stop=EMPTY_PAGE_STOP, show_page_progress=(WORKER_COUNT == 1),
        )
        error_rows = current_meta_df[current_meta_df['error'].fillna('').astype(str).str.strip() != ''] if 'error' in current_meta_df.columns else pd.DataFrame()
        if not error_rows.empty:
            error_text = '; '.join(error_rows['error'].astype(str).tolist())[:1000]
            return {
                'index': city_index, 'city': city_name, 'clean_df': current_clean_df,
                'summary': {'chengshi': city_name, 'jilu_shuliang': len(current_clean_df), 'zhuangtai': 'shibai', 'cuowu': error_text},
                'failure': {'chengshi': city_name, 'cuowu': error_text},
            }
        return {
            'index': city_index, 'city': city_name, 'clean_df': current_clean_df,
            'summary': {'chengshi': city_name, 'jilu_shuliang': len(current_clean_df), 'zhuangtai': 'chenggong', 'cuowu': ''},
            'failure': None,
        }
    except Exception as exc:
        error_text = repr(exc)
        return {
            'index': city_index, 'city': city_name, 'clean_df': pd.DataFrame(),
            'summary': {'chengshi': city_name, 'jilu_shuliang': 0, 'zhuangtai': 'shibai', 'cuowu': error_text},
            'failure': {'chengshi': city_name, 'cuowu': error_text},
        }


with ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
    futures = [executor.submit(crawl_city_task, index, city) for index, city in enumerate(ACTIVE_CITY_LIST)]
    results = [future.result() for future in as_completed(futures)]

for result in sorted(results, key=lambda item: item['index']):
    if not result['clean_df'].empty:
        city_clean_frames.append(result['clean_df'])
    city_summary_rows.append(result['summary'])
    if result['failure']:
        failed_cities.append(result['failure'])

all_clean_df = pd.concat(city_clean_frames, ignore_index=True) if city_clean_frames else pd.DataFrame()
city_summary_df = pd.DataFrame(city_summary_rows)
failed_city_df = pd.DataFrame(failed_cities)

db_result = save_crawl_result_to_mysql(all_clean_df, SCOPE, city_summary_df, failed_city_df, CRAWL_START_TIME)

print('\n关键词标识:', SCOPE['guanjianci_biaoshi'])
print('关键词:', KEYWORD)
print('统一城市列表:', SCOPE['chengshi_liebiao'])
print('运行状态:', db_result['yunxing_zhuangtai'])
print('是否替换原始快照:', db_result['shifou_tihuan'])
print('岗位记录数:', db_result['gangwei_jilu_shuliang'])
print('公司记录数:', db_result['gongsi_jilu_shuliang'])
print('招聘负责人记录数:', db_result['zhaopin_fuzeren_jilu_shuliang'])
print(city_summary_df.to_string(index=False))
if not failed_city_df.empty:
    print(failed_city_df.to_string(index=False))
