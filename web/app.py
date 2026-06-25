"""智联招聘数据分析 Flask API 与前端入口。"""

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from pymysql import MySQLError

from config import Config
from services.ai_service import AIAnalysisService, AIServiceError
from services.job_service import JobService
from services.redis_service import RedisService
from services.statistics_service import STATISTIC_TYPES, StatisticsService


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "static" / "dashboard"


def api_success(data, updated_at=None):
    return jsonify({"code": 0, "message": "success", "data": data, "updated_at": updated_at})


def api_error(code, message, http_status=400):
    return jsonify({"code": code, "message": message, "data": None}), http_status


def parse_int(name, default, minimum, maximum):
    raw = request.args.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} 必须是整数")
    if value < minimum or value > maximum:
        raise ValueError(f"{name} 必须在 {minimum}～{maximum} 之间")
    return value


def parse_optional_float(name):
    raw = request.args.get(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{name} 必须是数字")


def create_app():
    Config.validate()
    app = Flask(__name__, static_folder=str(BASE_DIR / "static"), static_url_path="/static")
    app.config.from_object(Config)
    app.json.ensure_ascii = False

    redis_service = RedisService(Config)
    statistics_service = StatisticsService(Config, redis_service)
    job_service = JobService(Config, redis_service)
    ai_service = AIAnalysisService(Config, redis_service, statistics_service, job_service)

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/api/health")
    def health():
        status = statistics_service.health()
        return api_success({**status, "api": True})

    @app.get("/api/scopes")
    def scopes():
        return api_success(job_service.get_scopes())

    @app.get("/api/dashboard/all")
    def dashboard_all():
        scope_id = request.args.get("scope_id", "").strip()
        if not scope_id:
            return api_error(4001, "缺少 scope_id")
        values, updated_at = statistics_service.get_statistics(scope_id)
        return api_success(values, updated_at)

    single_routes = {
        "summary": ["summary"],
        "city": ["city"],
        "salary": ["salary"],
        "education": ["education"],
        "experience": ["experience"],
        "industry": ["industry"],
        "skills": ["skills"],
        "company": ["company_size", "company_type", "financing", "top_companies"],
    }

    def register_dashboard_route(route_name, statistic_types):
        def handler():
            scope_id = request.args.get("scope_id", "").strip()
            if not scope_id:
                return api_error(4001, "缺少 scope_id")
            values, updated_at = statistics_service.get_statistics(scope_id, statistic_types)
            payload = values[statistic_types[0]] if len(statistic_types) == 1 else values
            return api_success(payload, updated_at)

        handler.__name__ = f"dashboard_{route_name}"
        app.add_url_rule(f"/api/dashboard/{route_name}", view_func=handler, methods=["GET"])

    for route_name, statistic_types in single_routes.items():
        register_dashboard_route(route_name, statistic_types)

    @app.get("/api/jobs")
    def jobs():
        scope_id = request.args.get("scope_id", "").strip()
        if not scope_id:
            return api_error(4001, "缺少 scope_id")
        params = {
            "scope_id": scope_id,
            "page": parse_int("page", 1, 1, 1000000),
            "page_size": parse_int("page_size", 10, 1, Config.MAX_PAGE_SIZE),
            "city": request.args.get("city", "").strip(),
            "education": request.args.get("education", "").strip(),
            "experience": request.args.get("experience", "").strip(),
            "company_size": request.args.get("company_size", "").strip(),
            "industry": request.args.get("industry", "").strip(),
            "salary_min": parse_optional_float("salary_min"),
            "salary_max": parse_optional_float("salary_max"),
            "keyword": request.args.get("keyword", "").strip(),
        }
        result = job_service.list_jobs(params)
        return api_success(result)

    @app.get("/api/jobs/<job_id>")
    def job_detail(job_id):
        return api_success(job_service.get_job(job_id))

    @app.get("/api/filters")
    def filters():
        scope_id = request.args.get("scope_id", "").strip()
        if not scope_id:
            return api_error(4001, "缺少 scope_id")
        return api_success(job_service.get_filters(scope_id))

    @app.get("/api/ai/summary")
    def ai_summary():
        scope_id = request.args.get("scope_id", "").strip()
        if not scope_id:
            return api_error(4001, "缺少 scope_id")
        return api_success(ai_service.generate_dashboard_summary(scope_id))

    @app.post("/api/ai/chat")
    def ai_chat():
        payload = request.get_json(silent=True) or {}
        scope_id = str(payload.get("scope_id", "")).strip()
        question = str(payload.get("question", "")).strip()
        if not scope_id:
            return api_error(4001, "缺少 scope_id")
        return api_success(ai_service.chat(scope_id, question))

    @app.get("/api/ai/job/<job_id>")
    def ai_job(job_id):
        return api_success(ai_service.analyze_job(job_id))

    @app.errorhandler(ValueError)
    def value_error(error):
        return api_error(4002, str(error), 400)

    @app.errorhandler(LookupError)
    def lookup_error(error):
        return api_error(4041, str(error), 404)

    @app.errorhandler(MySQLError)
    def mysql_error(error):
        app.logger.exception("MySQL 请求失败", exc_info=error)
        return api_error(5002, "MySQL 查询失败", 500)

    @app.errorhandler(AIServiceError)
    def ai_error(error):
        app.logger.warning("AI 请求失败: %s", error)
        return api_error(error.code, str(error), error.http_status)

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("未处理异常", exc_info=error)
        return api_error(5001, "服务器内部错误", 500)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(__import__("os").environ.get("FLASK_PORT", "5000")), debug=False)
