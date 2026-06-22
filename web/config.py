"""Flask 的本地 MySQL、Redis 和缓存配置。"""


class Config:
    MYSQL_HOST = "127.0.0.1"
    MYSQL_PORT = 3306
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""
    MYSQL_DATABASE = "shixun"

    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_PASSWORD = None
    REDIS_DATABASE = 0

    JSON_AS_ASCII = False
    MAX_PAGE_SIZE = 50
    JOBS_CACHE_TTL = 600
    JOB_DETAIL_CACHE_TTL = 3600
    FILTERS_CACHE_TTL = 21600
    EMPTY_RESULT_CACHE_TTL = 30

    @classmethod
    def validate(cls):
        return None
