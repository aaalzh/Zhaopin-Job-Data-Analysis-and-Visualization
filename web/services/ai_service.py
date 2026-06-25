"""大模型分析服务：组织数据、调用 OpenAI-compatible API，并缓存结果。"""

import hashlib
import json
import re
import socket
import textwrap
import urllib.error
import urllib.request
from datetime import datetime


class AIServiceError(Exception):
    def __init__(self, message, code=5004, http_status=503):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class AIAnalysisService:
    def __init__(self, config, redis_service, statistics_service, job_service):
        self.config = config
        self.redis = redis_service
        self.statistics = statistics_service
        self.jobs = job_service

    @staticmethod
    def _hash_text(value):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _chat_url(self):
        base_url = (self.config.AI_BASE_URL or "").strip().rstrip("/")
        if not base_url:
            raise AIServiceError("AI 服务未配置：请设置 AI_BASE_URL", 5003, 503)
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _ensure_configured(self):
        if not (self.config.AI_API_KEY or "").strip():
            raise AIServiceError("AI 服务未配置：请设置系统环境变量 AI_API_KEY", 5003, 503)
        if not (self.config.AI_MODEL or "").strip():
            raise AIServiceError("AI 服务未配置：请设置系统环境变量 AI_MODEL", 5003, 503)

    def _trim_value(self, value, list_limit=30, text_limit=1200):
        if isinstance(value, dict):
            return {key: self._trim_value(item, list_limit, text_limit) for key, item in value.items()}
        if isinstance(value, list):
            return [self._trim_value(item, list_limit, text_limit) for item in value[:list_limit]]
        if isinstance(value, str) and len(value) > text_limit:
            return value[:text_limit] + "...(已截断)"
        return value

    def _compact_statistics(self, values):
        compact = {}
        for statistic_type, payload in values.items():
            if isinstance(payload, dict) and "data" in payload:
                compact[statistic_type] = self._trim_value(payload.get("data"))
            else:
                compact[statistic_type] = self._trim_value(payload)
        return compact

    def _json_for_prompt(self, payload):
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        max_chars = self.config.AI_MAX_INPUT_CHARS
        if len(text) > max_chars:
            return text[:max_chars] + "\n...(输入数据已截断，只保留主要统计字段)"
        return text

    def _call_model(self, prompt):
        self._ensure_configured()
        request_body = {
            "model": self.config.AI_MODEL,
            "messages": [
                {"role": "system", "content": "你是严谨的中文招聘数据分析助手，只基于用户提供的数据回答。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.25,
            "max_tokens": self.config.AI_MAX_OUTPUT_TOKENS,
        }
        data = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._chat_url(),
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.AI_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.AI_TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")[:300]
            raise AIServiceError(f"大模型接口请求失败：{body or error.reason}", 5004, 503) from error
        except urllib.error.URLError as error:
            raise AIServiceError("AI 分析暂时不可用，请稍后重试", 5004, 503) from error
        except (TimeoutError, socket.timeout) as error:
            raise AIServiceError("AI 分析接口超时，请稍后重试", 5004, 503) from error
        except (TypeError, ValueError) as error:
            raise AIServiceError("大模型接口返回格式异常", 5004, 503) from error

        choices = response_data.get("choices") or []
        finish_reason = choices[0].get("finish_reason") if choices else None
        message = choices[0].get("message") if choices else {}
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not content and choices:
            content = choices[0].get("text")
        content = str(content or "").strip()
        if not content:
            raise AIServiceError("大模型返回内容为空", 5004, 503)
        if finish_reason == "length":
            raise AIServiceError("大模型输出被截断，请重新生成", 5004, 503)
        return content

    @staticmethod
    def _ends_with_heading(content):
        lines = [line.strip() for line in str(content or "").splitlines() if line.strip()]
        if not lines:
            return False
        last_line = lines[-1]
        return bool(
            re.match(r"^#{1,6}\s+\S+", last_line)
            or re.match(r"^\*\*[^*]+\*\*$", last_line)
            or re.match(r"^[一二三四五六七八九十]+[、.．]\s*\S+$", last_line)
            or re.match(r"^\d+[.、]\s*\S+$", last_line)
        )

    def _validate_complete_report(self, content):
        if self._ends_with_heading(content):
            raise AIServiceError("大模型返回的报告不完整，请重新生成", 5004, 503)

    def _cache_payload(self, content):
        return {
            "content": content,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def generate_dashboard_summary(self, scope_id):
        cache_key = f"zhaopin:ai:summary:{scope_id}"
        cached = self.redis.get_json(cache_key)
        if cached and cached.get("content"):
            return {**cached, "cached": True}

        self._ensure_configured()
        values, _ = self.statistics.get_statistics(scope_id)
        statistics_json = self._json_for_prompt({
            "scope_id": scope_id,
            "statistics": self._compact_statistics(values),
        })
        prompt = textwrap.dedent(f"""
            你是一个招聘数据分析助手，请根据给定的结构化招聘数据生成中文分析报告。

            要求：
            1. 只基于给定数据分析，不要编造不存在的信息。
            2. 不要输出大段连续正文，不要使用“好的，以下是”这类开场白。
            3. 使用 Markdown 小标题和短列表，每个要点尽量控制在 45 个汉字以内。
            4. 报告结构固定为：核心摘要、关键发现、分维度解读、求职建议。
            5. 从岗位规模、城市分布、薪资水平、学历经验要求、行业分布、技能需求等角度分析。
            6. 全文控制在 650～850 字，结论必须完整，不要在句子中间结束。

            统计数据：
            {statistics_json}

            请生成一份招聘数据分析报告。
        """).strip()
        content = self._call_model(prompt)
        self._validate_complete_report(content)
        payload = self._cache_payload(content)
        self.redis.set_json(cache_key, payload, self.config.AI_CACHE_TTL)
        return {**payload, "cached": False}

    def chat(self, scope_id, question):
        clean_question = str(question or "").strip()
        if not clean_question:
            raise ValueError("问题不能为空")
        if len(clean_question) > self.config.AI_MAX_QUESTION_CHARS:
            raise ValueError(f"问题长度不能超过 {self.config.AI_MAX_QUESTION_CHARS} 个字符")

        cache_key = f"zhaopin:ai:chat:{scope_id}:{self._hash_text(clean_question)}"
        cached = self.redis.get_json(cache_key)
        if cached and cached.get("answer"):
            return {**cached, "cached": True}

        self._ensure_configured()
        values, _ = self.statistics.get_statistics(scope_id)
        samples = []
        try:
            sample_result = self.jobs.list_jobs({
                "scope_id": scope_id,
                "page": 1,
                "page_size": 5,
                "city": "",
                "education": "",
                "experience": "",
                "company_size": "",
                "industry": "",
                "salary_min": None,
                "salary_max": None,
                "keyword": "",
            })
            samples = sample_result.get("items", [])
        except Exception:
            samples = []

        statistics_json = self._json_for_prompt({
            "scope_id": scope_id,
            "statistics": self._compact_statistics(values),
            "job_samples": self._trim_value(samples, list_limit=5, text_limit=500),
        })
        prompt = textwrap.dedent(f"""
            你是一个招聘数据分析助手。

            请根据以下招聘统计数据回答用户问题。
            如果数据中没有相关信息，请明确说明“当前数据不足以判断”，不要编造。

            招聘统计数据：
            {statistics_json}

            用户问题：
            {clean_question}
        """).strip()
        answer = self._call_model(prompt)
        payload = {
            "answer": answer,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.redis.set_json(cache_key, payload, self.config.AI_CACHE_TTL)
        return {**payload, "cached": False}

    def analyze_job(self, job_id):
        cache_key = f"zhaopin:ai:job:{job_id}"
        cached = self.redis.get_json(cache_key)
        if cached and cached.get("content"):
            return {**cached, "cached": True}

        self._ensure_configured()
        job_detail = self.jobs.get_job(job_id)
        job_json = self._json_for_prompt(self._trim_value(job_detail, list_limit=20, text_limit=2000))
        prompt = textwrap.dedent(f"""
            你是一个求职顾问，请根据以下岗位信息生成岗位分析。

            要求：
            1. 不要输出大段连续正文，不要使用“好的，以下是”这类开场白。
            2. 使用 Markdown 小标题和短列表，每个要点尽量控制在 45 个汉字以内。
            3. 每个小节给出 2～4 条重点，避免泛泛而谈。

            固定输出结构：
            1. 岗位核心要求
            2. 关键技能
            3. 适合人群
            4. 简历优化建议
            5. 面试准备建议
            6. 注意事项

            岗位信息：
            {job_json}
        """).strip()
        content = self._call_model(prompt)
        payload = self._cache_payload(content)
        self.redis.set_json(cache_key, payload, self.config.AI_CACHE_TTL)
        return {**payload, "cached": False}
