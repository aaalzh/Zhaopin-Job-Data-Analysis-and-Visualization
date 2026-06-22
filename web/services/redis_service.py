"""Redis JSON 缓存服务；连接失败时返回降级信号。"""

import json

import redis


class RedisService:
    def __init__(self, config):
        self.client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD,
            db=config.REDIS_DATABASE,
            decode_responses=True,
            socket_connect_timeout=1.5,
            socket_timeout=2.5,
        )

    def ping(self):
        try:
            return bool(self.client.ping())
        except redis.RedisError:
            return False

    def mget_json(self, keys):
        try:
            values = self.client.mget(keys)
        except redis.RedisError:
            return None
        result = []
        for value in values:
            if value is None:
                result.append(None)
                continue
            try:
                result.append(json.loads(value))
            except (TypeError, ValueError):
                result.append(None)
        return result

    def get_json(self, key):
        values = self.mget_json([key])
        return None if values is None else values[0]

    def set_many_json(self, values, ttl=None):
        if not values:
            return True
        try:
            pipeline = self.client.pipeline(transaction=False)
            for key, value in values.items():
                payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
                if ttl is None:
                    pipeline.set(key, payload)
                else:
                    pipeline.setex(key, ttl, payload)
            pipeline.execute()
            return True
        except redis.RedisError:
            return False

    def set_json(self, key, value, ttl):
        return self.set_many_json({key: value}, ttl=ttl)
