# 智联招聘岗位数据分析与可视化

这是一个本地可复现的实训项目，用于完成智联招聘岗位数据的采集、清洗、入仓、统计、缓存和可视化展示。当前仓库保留的是可直接运行的 `.py` 过程脚本、Hive SQL、Flask 后端和 React + ECharts 前端。

```text
智联招聘接口采集
-> MySQL 原始表
-> Spark 清洗
-> MySQL 清洗表 + HDFS/Hive 数仓
-> Spark 统计分析
-> MySQL 统计结果表
-> Redis 缓存
-> Flask API
-> React + ECharts 仪表盘
```

## 目录结构

```text
.
├── README.md
├── .gitignore
├── 爬虫/
│   └── 智联招聘岗位爬虫.py
├── 数据清洗上传HDFS/
│   └── Spark清洗并上传HDFS.py
├── 数据分析与缓存/
│   └── Spark岗位统计分析并写入Redis.py
├── sql/
│   ├── db_config.py
│   ├── 创建MySQL数据库.py
│   ├── 创建MySQL数据表.py
│   └── 清空MySQL数据.py
├── hive_shucang/
│   ├── chushihua_hive_shujuku.sql
│   └── jiazai_hive_shuju.sql
└── web/
    ├── app.py
    ├── config.py
    ├── services/
    ├── frontend/
    └── static/dashboard/
```

## 环境准备

需要提前安装并能正常启动：

- Python 3.x
- MySQL，默认数据库名为 `shixun`
- Redis，默认地址为 `127.0.0.1:6379`
- Hadoop、Spark、Hive
- Node.js 和 npm

Python 依赖可以按需安装：

```powershell
pip install pymysql flask redis requests pandas pyspark sqlalchemy tqdm
```

前端依赖在 `web/frontend/package.json` 中维护：

```powershell
cd web/frontend
npm install
```

## 本地配置

项目里的 Python 脚本和 Flask 服务不会把 MySQL 密码写死在仓库中，敏感值从系统环境变量读取。运行前至少设置：

```powershell
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="你的MySQL密码"
$env:MYSQL_DATABASE="shixun"
```

Redis 默认不需要密码。如果你的 Redis 设置了密码，再补充：

```powershell
$env:REDIS_HOST="127.0.0.1"
$env:REDIS_PORT="6379"
$env:REDIS_PASSWORD="你的Redis密码"
$env:REDIS_DATABASE="0"
```

如果使用 AI 分析功能，需要设置：

```powershell
$env:AI_API_KEY="你的API Key"
$env:AI_BASE_URL="https://api.deepseek.com"
$env:AI_MODEL="deepseek-v4-pro"
```

Spark 连接 MySQL 时需要 MySQL JDBC 驱动。清洗脚本会尝试从 Spark 目录查找，也可以显式指定：

```powershell
$env:MYSQL_JDBC_JAR="D:\path\to\mysql-connector-j-8.0.33.jar"
```

## 关键词参数

爬虫、清洗、Hive 装载和统计分析必须使用同一组关键词参数：

- `KEYWORD`：搜索关键词，例如 `数据分析`
- `KEYWORD_PATH_CODE` 或 `KEYWORD_CODE`：关键词代码，例如 `shuju_fenxi`
- `scope_id`：前后端接口使用的统计范围标识，等于关键词代码

当前文件里的默认值如下，完整重跑前要先统一：

| 文件 | 参数位置 | 当前默认值 |
| --- | --- | --- |
| `爬虫/智联招聘岗位爬虫.py` | `KEYWORD` / `KEYWORD_PATH_CODE` | `数据开发` / `shuju_kaifa` |
| `数据清洗上传HDFS/Spark清洗并上传HDFS.py` | `KEYWORD` / `KEYWORD_PATH_CODE` | `数据分析` / `shuju_fenxi` |
| `hive_shucang/jiazai_hive_shuju.sql` | `hivevar:guanjianci` / `hivevar:guanjianci_daima` | `数据分析` / `shuju_fenxi` |
| `数据分析与缓存/Spark岗位统计分析并写入Redis.py` | `KEYWORD` / `KEYWORD_CODE` | `数据开发` / `shuju_kaifa` |

如果要跑一条完整链路，先把上面四处改成同一个关键词和同一个关键词代码。城市列表只作为采集范围，不作为 MySQL 分表、Hive 分区或 Redis key 的区分条件。

## 运行流程

### 1. 创建 MySQL 数据库和表

在项目根目录运行：

```powershell
python sql/创建MySQL数据库.py
python sql/创建MySQL数据表.py
```

默认只创建不存在的表，不会删除旧数据。确认要删除并重建全部项目表时再运行：

```powershell
python sql/创建MySQL数据表.py --chongjian
```

当前 MySQL 表包括：

- 原始层：`yuan_shi_gangwei_xinxi`、`yuan_shi_gongsi_xinxi`、`yuan_shi_zhaopin_fuzeren_xinxi`
- 过程日志：`pachong_yunxing_rizhi`、`qingxi_yunxing_rizhi`
- 清洗层：`qingxi_gangwei_mingxi`、`qingxi_gongsi_xinxi`、`qingxi_zhaopin_fuzeren_xinxi`
- 统计层：`tongji_fenxi_jieguo`

### 2. 采集岗位数据

运行爬虫脚本：

```powershell
python "爬虫/智联招聘岗位爬虫.py"
```

脚本会调用智联招聘 JSON 接口，采集岗位、公司和招聘负责人信息，并写入 MySQL 原始表。成功写入时按 `guanjianci_biaoshi` 替换当前关键词旧快照；失败或部分失败时保留上一次成功数据。

### 3. Spark 清洗并上传 HDFS

运行清洗脚本：

```powershell
python "数据清洗上传HDFS/Spark清洗并上传HDFS.py"
```

脚本从 MySQL 原始表读取当前关键词数据，完成字段清洗、薪资规范化、去重等处理，并写入：

- MySQL 清洗表
- HDFS 清洗快照：`/user/10967/zhilian_zhaopin/qingxi_jieguo/<scope_id>/qingxi_gangwei.csv`
- Hive 输入文件：`/user/10967/zhilian_zhaopin/shucang/yuan_shi_gangwei_qingxi/guanjianci_daima=<scope_id>/qingxi_gangwei.csv`

当前 Hive 装载 SQL 实际读取的是：

```text
/user/10967/zhilian_zhaopin/qingxi_jieguo/<scope_id>
```

所以如果清洗脚本或 Hive SQL 的路径后续调整，需要同步检查这两处是否一致。

### 4. 初始化并装载 Hive 数仓

先初始化 Hive 数据库：

```powershell
hive -f hive_shucang/chushihua_hive_shujuku.sql
```

再打开 `hive_shucang/jiazai_hive_shuju.sql`，确认顶部变量和当前重跑关键词一致：

```sql
SET hivevar:guanjianci=数据分析;
SET hivevar:guanjianci_daima=shuju_fenxi;
```

确认后执行：

```powershell
hive -f hive_shucang/jiazai_hive_shuju.sql
```

装载脚本会按关键词代码生成三张表：

- `yuan_shi_gangwei_qingxi_<scope_id>`
- `mingxi_gangwei_xinxi_<scope_id>`
- `mingxi_gangwei_jineng_<scope_id>`

### 5. 运行 Spark 统计并写入 Redis

运行统计脚本：

```powershell
python "数据分析与缓存/Spark岗位统计分析并写入Redis.py"
```

统计脚本默认 `DATA_SOURCE = "hive"`，会读取：

- `zhaopin_shucang.mingxi_gangwei_xinxi_<scope_id>`
- `zhaopin_shucang.mingxi_gangwei_jineng_<scope_id>`

统计结果先写入 MySQL 表 `tongji_fenxi_jieguo`，MySQL 提交成功后再同步到 Redis。Redis key 格式为：

```text
zhaopin:dashboard:<统计类型>:<scope_id>
```

当前统计类型包括：

- `summary`
- `city`
- `salary`
- `education`
- `experience`
- `company_size`
- `company_type`
- `financing`
- `top_companies`
- `industry`
- `publish_trend`
- `skills`

### 6. 启动 Flask 后端

```powershell
cd web
python app.py
```

默认访问地址：

```text
http://127.0.0.1:5000
```

如需修改端口：

```powershell
$env:FLASK_PORT="5003"
python app.py
```

### 7. 启动或构建前端

开发模式：

```powershell
cd web/frontend
npm run dev
```

Vite 开发服务默认监听 `127.0.0.1:5173`，并把 `/api` 代理到 `http://127.0.0.1:5000`。

构建静态文件：

```powershell
cd web/frontend
npm run build
```

构建产物输出到 `web/static/dashboard/`，Flask 根路径 `/` 会直接返回构建后的前端页面。Vite 的静态资源基础路径为 `/static/dashboard/`。

## 主要 API

Flask 后端入口为 `web/app.py`。接口统一返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "updated_at": null
}
```

主要接口：

```text
GET  /api/health
GET  /api/scopes
GET  /api/dashboard/all?scope_id=<scope_id>
GET  /api/dashboard/summary?scope_id=<scope_id>
GET  /api/dashboard/city?scope_id=<scope_id>
GET  /api/dashboard/salary?scope_id=<scope_id>
GET  /api/dashboard/education?scope_id=<scope_id>
GET  /api/dashboard/experience?scope_id=<scope_id>
GET  /api/dashboard/industry?scope_id=<scope_id>
GET  /api/dashboard/skills?scope_id=<scope_id>
GET  /api/dashboard/company?scope_id=<scope_id>
GET  /api/jobs?scope_id=<scope_id>&page=1&page_size=10
GET  /api/jobs/<job_id>
GET  /api/filters?scope_id=<scope_id>
GET  /api/ai/summary?scope_id=<scope_id>
POST /api/ai/chat
GET  /api/ai/job/<job_id>
```

岗位列表支持的筛选参数：

```text
city
education
experience
company_size
industry
salary_min
salary_max
keyword
```

## 数据和提交说明

仓库 `.gitignore` 已排除运行生成的数据文件和依赖目录：

```text
data/
**/清洗后的数据/
*.csv
*.xlsx
__pycache__/
*.py[cod]
node_modules/
.npm-cache/
```

可以提交代码、SQL、前端源码和构建后的仪表盘静态文件。采集结果、清洗结果、CSV/XLSX、依赖目录和本机缓存不应提交。

## 常见检查

页面没有数据时，按顺序检查：

1. `MYSQL_PASSWORD` 是否已经在当前 PowerShell 窗口设置。
2. MySQL 中是否有 `qingxi_gangwei_mingxi` 和 `tongji_fenxi_jieguo` 数据。
3. Redis 是否已启动，端口是否为 `6379`。
4. `/api/health` 是否显示 MySQL 和 Redis 正常。
5. `/api/scopes` 是否能查到当前 `scope_id`。
6. 前端选择的 `scope_id` 是否和爬虫、清洗、Hive、统计脚本一致。
7. 修改后是否重启了正在运行的 Flask 进程。

AI 接口不可用时，按顺序检查：

1. `AI_API_KEY` 是否已经设置。
2. `AI_BASE_URL` 和 `AI_MODEL` 是否与当前服务商匹配。
3. Flask 是否仍由旧进程占用端口。
4. 旧的 AI 结果是否仍缓存在 Redis 中。

## 清空重跑

只清空 MySQL 项目表数据并保留表结构：

```powershell
python sql/清空MySQL数据.py
```

完整重跑时建议按这个顺序处理：

1. 统一爬虫、清洗、Hive、统计四处关键词参数。
2. 清空 MySQL 项目表。
3. 删除或重建 HDFS 中当前项目输出目录。
4. 清理 Redis 中 `zhaopin:*` 相关 key。
5. 重新执行爬虫、清洗、Hive 装载、Spark 统计、Flask 和前端。

执行删除 HDFS 或 Redis 数据前，先确认当前关键词和路径，避免误删其他项目数据。
