"""Flask 的本地 MySQL、Redis、大模型和缓存配置。"""

import os


def _env_str(name, default=""):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _env_int(name, default):
    return int(_env_str(name, str(default)))


def _env_optional(name):
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return value


class Config:
    MYSQL_HOST = _env_str("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = _env_int("MYSQL_PORT", 3306)
    MYSQL_USER = _env_str("MYSQL_USER", "root")
    MYSQL_PASSWORD = _env_str("MYSQL_PASSWORD")
    MYSQL_DATABASE = _env_str("MYSQL_DATABASE", "shixun")

    REDIS_HOST = _env_str("REDIS_HOST", "127.0.0.1")
    REDIS_PORT = _env_int("REDIS_PORT", 6379)
    REDIS_PASSWORD = _env_optional("REDIS_PASSWORD")
    REDIS_DATABASE = _env_int("REDIS_DATABASE", 0)

    JSON_AS_ASCII = False
    MAX_PAGE_SIZE = 50
    JOBS_CACHE_TTL = 600
    JOB_DETAIL_CACHE_TTL = 3600
    FILTERS_CACHE_TTL = 21600
    EMPTY_RESULT_CACHE_TTL = 30

    AI_API_KEY = _env_str("AI_API_KEY")
    AI_BASE_URL = _env_str("AI_BASE_URL", "https://api.deepseek.com")
    AI_MODEL = _env_str("AI_MODEL", "deepseek-v4-pro")
    AI_TIMEOUT = _env_int("AI_TIMEOUT", 90)
    AI_MAX_OUTPUT_TOKENS = _env_int("AI_MAX_OUTPUT_TOKENS", 3000)
    AI_CACHE_TTL = 3600
    AI_MAX_INPUT_CHARS = 24000
    AI_MAX_QUESTION_CHARS = 300

    @classmethod
    def validate(cls):
        missing = []
        if not cls.MYSQL_PASSWORD:
            missing.append("MYSQL_PASSWORD")
        if missing:
            raise RuntimeError("缺少系统环境变量: " + ", ".join(missing))
        return None
