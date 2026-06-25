"""仪表盘统计读取：Redis 优先，MySQL 回源并回填。"""

import json

import pymysql


STATISTIC_TYPES = [
    "summary",
    "city",
    "salary",
    "education",
    "experience",
    "company_size",
    "company_type",
    "financing",
    "top_companies",
    "industry",
    "publish_trend",
    "skills",
]


class StatisticsService:
    def __init__(self, config, redis_service):
        self.config = config
        self.redis = redis_service

    def _mysql_connection(self):
        return pymysql.connect(
            host=self.config.MYSQL_HOST,
            port=self.config.MYSQL_PORT,
            user=self.config.MYSQL_USER,
            password=self.config.MYSQL_PASSWORD,
            database=self.config.MYSQL_DATABASE,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=4,
        )

    @staticmethod
    def redis_key(statistic_type, scope_id):
        return f"zhaopin:dashboard:{statistic_type}:{scope_id}"

    def get_statistics(self, scope_id, statistic_types=None):
        requested = statistic_types or STATISTIC_TYPES
        keys = [self.redis_key(item, scope_id) for item in requested]
        cached_values = self.redis.mget_json(keys)
        result = {}
        missing = []

        if cached_values is None:
            missing = list(requested)
        else:
            for statistic_type, cached in zip(requested, cached_values):
                if isinstance(cached, dict):
                    result[statistic_type] = cached
                else:
                    missing.append(statistic_type)

        if missing:
            placeholders = ",".join(["%s"] * len(missing))
            sql = f"""
                SELECT tongji_leixing, jieguo_json
                FROM tongji_fenxi_jieguo
                WHERE guanjianci_biaoshi = %s
                  AND tongji_leixing IN ({placeholders})
            """
            with self._mysql_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, [scope_id] + missing)
                    rows = cursor.fetchall()

            restored = {}
            for row in rows:
                try:
                    parsed = json.loads(row["jieguo_json"])
                except (TypeError, ValueError):
                    continue
                statistic_type = row["tongji_leixing"]
                result[statistic_type] = parsed
                restored[self.redis_key(statistic_type, scope_id)] = parsed
            self.redis.set_many_json(restored)

        absent = [item for item in requested if item not in result]
        if absent:
            raise LookupError("统计数据不存在: " + ", ".join(absent))

        updated_values = [item.get("updated_at") for item in result.values() if item.get("updated_at")]
        return result, max(updated_values) if updated_values else None

    def health(self):
        mysql_ok = False
        try:
            with self._mysql_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    mysql_ok = cursor.fetchone() is not None
        except pymysql.MySQLError:
            mysql_ok = False
        return {"mysql": mysql_ok, "redis": self.redis.ping()}
