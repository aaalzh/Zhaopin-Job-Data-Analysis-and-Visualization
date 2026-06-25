"""岗位分页、筛选、详情和筛选项服务。"""

import hashlib
import html
import json
import re

import pymysql


class JobService:
    LIST_COLUMNS = """
        gangwei_weiyi_biaoshi AS job_id,
        zhiwei_mingcheng AS job_name,
        laiyuan_chengshi AS city,
        zuidi_xinzi AS salary_min,
        zuigao_xinzi AS salary_max,
        xueli_yaoqiu AS education,
        jingyan_yaoqiu AS experience,
        gongsi_mingcheng AS company_name,
        gongsi_guimo AS company_size,
        gongsi_xingzhi AS company_type,
        hangye AS industry,
        fabu_shijian AS publish_time
    """

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
    def _cache_hash(params):
        payload = json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _text(value):
        return str(value or "").strip()

    @staticmethod
    def _plain_description(value):
        text = html.unescape(str(value or ""))
        text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<\s*/?\s*(div|p|li|ul|ol)\b[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        return text.strip()

    def _build_filters(self, params):
        clauses = ["guanjianci_biaoshi = %s"]
        values = [params["scope_id"]]
        field_map = {
            "city": "laiyuan_chengshi",
            "education": "xueli_yaoqiu",
            "experience": "jingyan_yaoqiu",
            "company_size": "gongsi_guimo",
            "industry": "hangye",
        }
        for name, column in field_map.items():
            value = self._text(params.get(name))
            if value:
                clauses.append(f"{column} = %s")
                values.append(value)

        keyword = self._text(params.get("keyword"))
        if keyword:
            wildcard = f"%{keyword}%"
            clauses.append(
                "(zhiwei_mingcheng LIKE %s OR gongsi_mingcheng LIKE %s "
                "OR jineng_biaoqian LIKE %s OR zhiwei_miaoshu LIKE %s)"
            )
            values.extend([wildcard] * 4)

        salary_min = params.get("salary_min")
        salary_max = params.get("salary_max")
        low_expression = "CAST(NULLIF(REPLACE(zuidi_xinzi, '万', ''), '') AS DECIMAL(10,2))"
        high_expression = "CAST(NULLIF(REPLACE(zuigao_xinzi, '万', ''), '') AS DECIMAL(10,2))"
        if salary_min is not None:
            clauses.append(f"{high_expression} >= %s")
            values.append(salary_min)
        if salary_max is not None:
            clauses.append(f"{low_expression} <= %s")
            values.append(salary_max)
        return " AND ".join(clauses), values

    def list_jobs(self, params):
        cache_key = f"zhaopin:jobs:{params['scope_id']}:{self._cache_hash(params)}"
        cached = self.redis.get_json(cache_key)
        if cached is not None:
            return cached

        where_sql, values = self._build_filters(params)
        offset = (params["page"] - 1) * params["page_size"]
        count_sql = f"SELECT COUNT(*) AS total FROM qingxi_gangwei_mingxi WHERE {where_sql}"
        data_sql = f"""
            SELECT {self.LIST_COLUMNS}
            FROM qingxi_gangwei_mingxi
            WHERE {where_sql}
            ORDER BY fabu_shijian DESC, zizeng_bianhao DESC
            LIMIT %s OFFSET %s
        """
        with self._mysql_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(count_sql, values)
                total = int(cursor.fetchone()["total"])
                cursor.execute(data_sql, values + [params["page_size"], offset])
                items = cursor.fetchall()

        result = {
            "items": items,
            "pagination": {
                "page": params["page"],
                "page_size": params["page_size"],
                "total": total,
                "pages": max(1, (total + params["page_size"] - 1) // params["page_size"]),
            },
        }
        ttl = self.config.EMPTY_RESULT_CACHE_TTL if total == 0 else self.config.JOBS_CACHE_TTL
        self.redis.set_json(cache_key, result, ttl)
        return result

    def get_job(self, job_id):
        cache_key = f"zhaopin:job:{job_id}"
        cached = self.redis.get_json(cache_key)
        if cached is not None:
            cached["description"] = self._plain_description(cached.get("description"))
            return cached
        sql = """
            SELECT
                gangwei_weiyi_biaoshi AS job_id,
                zhiwei_mingcheng AS job_name,
                laiyuan_chengshi AS city,
                gongzuo_didian AS address,
                zuidi_xinzi AS salary_min,
                zuigao_xinzi AS salary_max,
                xueli_yaoqiu AS education,
                jingyan_yaoqiu AS experience,
                gongzuo_leixing AS job_type,
                gongzuo_moshi AS work_mode,
                zhiwei_leibie AS category,
                gongsi_mingcheng AS company_name,
                gongsi_guimo AS company_size,
                gongsi_xingzhi AS company_type,
                rongzi_jieduan AS financing,
                hangye AS industry,
                fabu_shijian AS publish_time,
                zhaopin_fuzeren_zhuangtai AS recruiter_status,
                zhaopin_fuzeren_huoyue_biaoqian AS recruiter_activity,
                jineng_biaoqian AS skills,
                zhiwei_miaoshu AS description
            FROM qingxi_gangwei_mingxi
            WHERE gangwei_weiyi_biaoshi = %s
            LIMIT 1
        """
        with self._mysql_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (job_id,))
                result = cursor.fetchone()
        if result is None:
            raise LookupError("岗位不存在")
        result["description"] = self._plain_description(result.get("description"))
        self.redis.set_json(cache_key, result, self.config.JOB_DETAIL_CACHE_TTL)
        return result

    def get_filters(self, scope_id):
        cache_key = f"zhaopin:filters:{scope_id}"
        cached = self.redis.get_json(cache_key)
        if cached is not None:
            return cached
        columns = {
            "cities": "laiyuan_chengshi",
            "educations": "xueli_yaoqiu",
            "experiences": "jingyan_yaoqiu",
            "company_sizes": "gongsi_guimo",
            "industries": "hangye",
        }
        result = {}
        with self._mysql_connection() as connection:
            with connection.cursor() as cursor:
                for output_name, column in columns.items():
                    cursor.execute(
                        f"""
                        SELECT DISTINCT {column} AS value
                        FROM qingxi_gangwei_mingxi
                        WHERE guanjianci_biaoshi = %s
                          AND {column} IS NOT NULL
                          AND TRIM({column}) <> ''
                        ORDER BY {column}
                        """,
                        (scope_id,),
                    )
                    result[output_name] = [row["value"] for row in cursor.fetchall()]
        self.redis.set_json(cache_key, result, self.config.FILTERS_CACHE_TTL)
        return result

    def get_scopes(self):
        sql = """
            SELECT guanjianci_biaoshi AS scope_id,
                   MAX(guanjianci) AS keyword,
                   MAX(chengshi_liebiao) AS cities,
                   COUNT(*) AS job_count,
                   MAX(chuangjian_shijian) AS updated_at
            FROM qingxi_gangwei_mingxi
            GROUP BY guanjianci_biaoshi
            ORDER BY updated_at DESC
        """
        with self._mysql_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()
