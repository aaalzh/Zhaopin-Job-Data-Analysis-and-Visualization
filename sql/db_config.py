"""MySQL 连接配置：涉密值只从系统环境变量读取。"""

import os


def _env_str(name, default=""):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _env_int(name, default):
    return int(_env_str(name, str(default)))


def _required_env(name):
    value = _env_str(name)
    if not value:
        raise RuntimeError(f"请先设置系统环境变量 {name}")
    return value


MYSQL_HOST = _env_str("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = _env_int("MYSQL_PORT", 3306)
MYSQL_USER = _env_str("MYSQL_USER", "root")
MYSQL_PASSWORD = _required_env("MYSQL_PASSWORD")
MYSQL_DATABASE = _env_str("MYSQL_DATABASE", "shixun")
