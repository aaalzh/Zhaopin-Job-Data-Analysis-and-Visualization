import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BankOutlined,
  BarChartOutlined,
  CarryOutOutlined,
  CalendarOutlined,
  CloseOutlined,
  EnvironmentOutlined,
  MessageOutlined,
  MoneyCollectOutlined,
  ReloadOutlined,
  RobotOutlined,
  SearchOutlined,
  SendOutlined,
} from "@ant-design/icons";
import { apiGet, apiPost } from "./api.js";
import { Chart, echarts } from "./Chart.jsx";

const COLORS = ["#1268f3", "#13b7d4", "#19c59d", "#ffb437", "#ff7d59", "#8b6ee8", "#ec6d9d"];
const EMPTY_FILTERS = {
  keyword: "",
  city: "",
  experience: "",
  education: "",
  company_size: "",
  industry: "",
  salary_min: "",
  salary_max: "",
};

const CITY_COORDINATES = {
  北京: [116.4, 39.9], 上海: [121.47, 31.23], 广州: [113.26, 23.13], 深圳: [114.06, 22.55],
  天津: [117.2, 39.12], 武汉: [114.31, 30.59], 西安: [108.94, 34.34], 成都: [104.07, 30.67],
  大连: [121.61, 38.91], 长春: [125.32, 43.82], 沈阳: [123.43, 41.8], 南京: [118.8, 32.06],
  济南: [117.12, 36.65], 青岛: [120.38, 36.07], 杭州: [120.15, 30.27], 苏州: [120.59, 31.3],
  无锡: [120.31, 31.49], 宁波: [121.55, 29.87], 重庆: [106.55, 29.56], 郑州: [113.63, 34.75],
  长沙: [112.94, 28.23], 福州: [119.3, 26.08], 厦门: [118.09, 24.48], 哈尔滨: [126.64, 45.76],
};

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

function salaryText(job) {
  if (!job) return "—";
  const low = job.salary_min || "";
  const high = job.salary_max || "";
  return low || high ? `${low || "—"}–${high || "—"}` : "面议";
}

function dataOf(dashboard, type) {
  return dashboard?.[type]?.data || null;
}

function commonChart() {
  return {
    animationDuration: 450,
    color: COLORS,
    textStyle: { fontFamily: "Segoe UI, Microsoft YaHei, sans-serif", color: "#55647a" },
    tooltip: { trigger: "item", confine: true, backgroundColor: "rgba(20,36,63,.92)", borderWidth: 0, textStyle: { color: "#fff" } },
  };
}

function pieOption(data) {
  const pairs = (data?.categories || []).map((name, index) => ({ name, value: data?.values?.[index] || 0 })).sort((a, b) => b.value - a.value);
  const visible = pairs.slice(0, 6);
  const otherValue = pairs.slice(6).reduce((sum, item) => sum + Number(item.value || 0), 0);
  if (otherValue > 0) visible.push({ name: "其他", value: otherValue });
  return {
    ...commonChart(),
    legend: { orient: "vertical", right: 4, top: "middle", itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 10, color: "#607087" } },
    series: [{
      type: "pie",
      radius: ["47%", "70%"],
      center: ["28%", "52%"],
      minAngle: 4,
      avoidLabelOverlap: false,
      label: { show: false, position: "center" },
      labelLine: { show: false },
      data: visible,
    }],
  };
}

function PieChart({ data, centerText, ariaLabel }) {
  return (
    <div className="pie-chart-wrap">
      <Chart option={pieOption(data)} className="pie-chart-canvas" ariaLabel={ariaLabel} />
      {centerText && <span className="pie-center-text">{centerText}</span>}
    </div>
  );
}

function horizontalBarOption(data, limit = 15) {
  const categories = (data?.categories || []).slice(0, limit);
  const values = (data?.values || data?.job_counts || []).slice(0, limit);
  return {
    ...commonChart(),
    grid: { left: 88, right: 18, top: 14, bottom: 26 },
    xAxis: { type: "value", axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: "#edf1f6" } } },
    yAxis: { type: "category", inverse: true, data: categories, axisLabel: { width: 76, overflow: "truncate", fontSize: 10 }, axisTick: { show: false }, axisLine: { show: false } },
    series: [{ type: "bar", data: values, barWidth: 8, itemStyle: { color: "#1974f5", borderRadius: [0, 5, 5, 0] }, label: { show: true, position: "right", fontSize: 9, color: "#6a7890" } }],
  };
}

function trendOption(data) {
  return {
    ...commonChart(),
    grid: { left: 48, right: 20, top: 18, bottom: 34 },
    xAxis: { type: "category", boundaryGap: false, data: data?.categories || [], axisLabel: { fontSize: 10, hideOverlap: true }, axisTick: { show: false }, axisLine: { lineStyle: { color: "#d9e1ec" } } },
    yAxis: { type: "value", axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: "#edf1f6" } } },
    series: [{ type: "line", smooth: 0.3, symbolSize: 5, data: data?.values || [], lineStyle: { width: 2, color: "#1674f8" }, itemStyle: { color: "#1674f8" }, areaStyle: { color: "rgba(22,116,248,.08)" } }],
  };
}

function skillsOption(data) {
  return {
    ...commonChart(),
    grid: { left: 46, right: 18, top: 18, bottom: 50 },
    xAxis: { type: "category", data: data?.categories || [], axisLabel: { interval: 0, rotate: 38, fontSize: 9 }, axisTick: { show: false }, axisLine: { lineStyle: { color: "#d9e1ec" } } },
    yAxis: { type: "value", axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: "#edf1f6" } } },
    series: [{ type: "bar", barMaxWidth: 16, data: data?.values || [], itemStyle: { color: "#1f7bf5", borderRadius: [4, 4, 0, 0] } }],
  };
}

function CityMap({ data }) {
  const [mapReady, setMapReady] = useState(Boolean(echarts.getMap("china")));
  useEffect(() => {
    if (echarts.getMap("china")) return;
    fetch("/static/dashboard/china.json")
      .then((response) => response.json())
      .then((geoJson) => { echarts.registerMap("china", geoJson); setMapReady(true); })
      .catch(() => setMapReady(false));
  }, []);

  const option = useMemo(() => {
    if (!mapReady) return horizontalBarOption(data, 12);
    const points = (data?.categories || []).map((name, index) => {
      const coord = CITY_COORDINATES[name];
      return coord ? { name, value: [...coord, data.job_counts?.[index] || 0] } : null;
    }).filter(Boolean);
    const max = Math.max(1, ...points.map((point) => point.value[2]));
    return {
      ...commonChart(),
      geo: {
        map: "china",
        roam: false,
        layoutCenter: ["54%", "53%"],
        layoutSize: "118%",
        itemStyle: { areaColor: "#e7f1ff", borderColor: "#b7cff0" },
        emphasis: { itemStyle: { areaColor: "#bedaff" }, label: { show: false } },
      },
      visualMap: { min: 0, max, left: 24, top: "middle", calculable: false, text: ["高", "低"], itemHeight: 190, itemWidth: 28, inRange: { color: ["#b9d8ff", "#146ff3"] }, textStyle: { fontSize: 11 } },
      series: [{ type: "effectScatter", coordinateSystem: "geo", data: points, symbolSize: (value) => 5 + 12 * Math.sqrt(value[2] / max), rippleEffect: { scale: 2.2, brushType: "stroke" }, itemStyle: { color: "#0d6ff1" }, tooltip: { formatter: (item) => `${item.name}<br/>岗位数：${formatNumber(item.value[2])}` } }],
    };
  }, [data, mapReady]);
  return <Chart option={option} className="city-map" ariaLabel="城市岗位分布地图" />;
}

function Kpi({ icon, label, value, suffix, note, tone }) {
  return (
    <div className="kpi">
      <div className={`kpi-icon ${tone}`}>{icon}</div>
      <div><span>{label}</span><strong>{value}{suffix && <small>{suffix}</small>}</strong><em>{note}</em></div>
    </div>
  );
}

function Panel({ title, children, className = "" }) {
  return <section className={`panel ${className}`}><h2>{title}</h2>{children}</section>;
}

function renderRichText(text) {
  const parts = String(text || "").split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

function normalizeAiHeading(text) {
  return String(text || "")
    .replace(/^#{1,6}\s*/, "")
    .replace(/^\*\*(.+)\*\*$/, "$1")
    .replace(/^【(.+)】$/, "$1")
    .replace(/^[一二三四五六七八九十]+[、.．]\s*/, "")
    .replace(/^\d+[.、]\s*/, "")
    .trim();
}

function getAiHeading(line) {
  const raw = String(line || "").trim();
  if (!raw) return null;
  const noHash = raw.replace(/^#{1,6}\s*/, "").trim();
  const titledBodyMatch = noHash.match(/^\*\*(.+?)\*\*\s*[:：]\s*(.+)$/);
  const boldMatch = noHash.match(/^\*\*(.+)\*\*$/);
  const plain = (boldMatch ? boldMatch[1] : noHash).trim();
  const looksLikeHeading = raw.startsWith("#")
    || Boolean(boldMatch)
    || /^[一二三四五六七八九十]+[、.．]\s*/.test(plain)
    || /^\d+[.、]\s*/.test(plain)
    || /^【[^】]+】$/.test(plain);
  if (!looksLikeHeading) return null;
  if (titledBodyMatch) {
    return { title: normalizeAiHeading(titledBodyMatch[1]), body: titledBodyMatch[2].trim() };
  }
  return { title: normalizeAiHeading(plain), body: "" };
}

function getAiBullet(line) {
  const match = String(line || "").trim().match(/^[-*]\s+(.+)$/);
  return match ? match[1].trim() : "";
}

function isGenericAiPreface(line) {
  return /^(好的|当然|可以)[，,]\s*(以下|基于|根据)/.test(String(line || "").trim());
}

function firstSentence(text) {
  const match = String(text || "").match(/^(.+?[。！？；]|.+?$)/);
  return match ? match[1].trim() : "";
}

function parseAiReport(content) {
  const lines = String(content || "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && !/^[-_*]{3,}$/.test(line));
  const report = { intro: [], sections: [] };
  let current = null;

  lines.forEach((line) => {
    if (!current && report.intro.length === 0 && isGenericAiPreface(line)) {
      return;
    }

    const bullet = getAiBullet(line);
    if (bullet) {
      if (!current) {
        current = { title: "重点内容", body: [], bullets: [] };
        report.sections.push(current);
      }
      current.bullets.push(bullet);
      return;
    }

    const heading = getAiHeading(line);
    if (heading) {
      current = { title: heading.title, body: heading.body ? [heading.body] : [], bullets: [] };
      report.sections.push(current);
      return;
    }

    if (current) {
      current.body.push(line);
    } else {
      report.intro.push(line);
    }
  });

  report.sections = report.sections.filter((section) => section.body.length || section.bullets.length);
  report.highlights = [];
  return report;
}

function AiText({ content, empty = "暂无 AI 分析内容" }) {
  const lines = (content || "").split(/\n+/).map((line) => line.trim()).filter(Boolean);
  return (
    <div className="ai-text">
      {lines.length ? lines.map((line, index) => <p key={`${line}-${index}`}>{renderRichText(line)}</p>) : <p>{empty}</p>}
    </div>
  );
}

function AiStructuredReport({ content, empty = "暂无 AI 分析内容", compact = false }) {
  const report = useMemo(() => parseAiReport(content), [content]);
  const hasContent = report.intro.length || report.sections.length;
  if (!hasContent) {
    return <div className={`ai-report ${compact ? "compact" : ""}`}><p className="ai-empty">{empty}</p></div>;
  }

  return (
    <div className={`ai-report ${compact ? "compact" : ""}`}>
      {report.intro.length > 0 && (
        <section className="ai-report-overview">
          <span>核心摘要</span>
          {report.intro.slice(0, 2).map((paragraph, index) => <p key={`${paragraph}-${index}`}>{renderRichText(paragraph)}</p>)}
        </section>
      )}

      {!compact && report.highlights.length > 0 && (
        <div className="ai-highlight-grid">
          {report.highlights.map((item, index) => (
            <section className="ai-highlight" key={`${item.title}-${index}`}>
              <b>{String(index + 1).padStart(2, "0")}</b>
              <strong>{item.title}</strong>
              <p>{renderRichText(item.text)}</p>
            </section>
          ))}
        </div>
      )}

      {report.sections.length > 0 && (
        <div className="ai-section-list">
          {report.sections.map((section, index) => (
            <section className="ai-report-section" key={`${section.title}-${index}`}>
              <div className="ai-report-section-head">
                <b>{index + 1}</b>
                <h3>{renderRichText(section.title || "分析内容")}</h3>
              </div>
              {section.body.map((paragraph, paragraphIndex) => (
                <p key={`${paragraph}-${paragraphIndex}`}>{renderRichText(paragraph)}</p>
              ))}
              {section.bullets.length > 0 && (
                <ul>
                  {section.bullets.map((item, itemIndex) => <li key={`${item}-${itemIndex}`}>{renderRichText(item)}</li>)}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function AiSummaryDrawer({ open, content, loading, error, generatedAt, cached, onClose }) {
  if (!open) return null;
  return (
    <div className="drawer-backdrop" onMouseDown={onClose}>
      <aside className="ai-drawer" onMouseDown={(event) => event.stopPropagation()} aria-label="AI 数据解读">
        <button className="drawer-close" onClick={onClose} aria-label="关闭 AI 解读"><CloseOutlined /></button>
        <div className="drawer-heading ai-heading">
          <span>AI 解读</span>
          <h2>招聘数据分析报告</h2>
          <p>{generatedAt ? `${cached ? "缓存生成" : "生成时间"}：${generatedAt}` : "基于当前关键词生成"}</p>
        </div>
        <div className="ai-result-body">
          {loading && <div className="drawer-loading">正在生成 AI 解读…</div>}
          {!loading && error && <div className="ai-error">{error}</div>}
          {!loading && !error && <AiStructuredReport content={content} />}
        </div>
      </aside>
    </div>
  );
}

function FilterSelect({ label, value, values, onChange }) {
  return (
    <label className="filter-control"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}><option value="">全部</option>{(values || []).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
  );
}

function JobDrawer({ job, loading, onClose, aiAnalysis, aiLoading, aiError, onAnalyzeJob }) {
  if (!job && !loading) return null;
  const skillList = (job?.skills || "").split("|").map((item) => item.trim()).filter(Boolean).slice(0, 12);
  const hasCurrentAi = aiAnalysis?.jobId === job?.job_id;
  return (
    <div className="drawer-backdrop" onMouseDown={onClose}>
      <aside className="job-drawer" onMouseDown={(event) => event.stopPropagation()} aria-label="岗位详情">
        <button className="drawer-close" onClick={onClose} aria-label="关闭岗位详情"><CloseOutlined /></button>
        {loading ? <div className="drawer-loading">正在加载岗位详情…</div> : <>
          <div className="drawer-heading"><span>岗位详情</span><h2>{job.job_name}</h2><strong>{salaryText(job)}</strong><p>{job.city} · {job.education || "学历不限"} · {job.experience || "经验不限"} · {job.job_type || "全职"}</p></div>
          <div className="company-summary"><BankOutlined /><div><strong>{job.company_name}</strong><p>{job.company_type} · {job.company_size} · {job.financing || "融资信息未知"}</p></div></div>
          <div className="drawer-section"><h3>职位描述</h3><p className="job-description">{job.description || "暂无职位描述"}</p></div>
          <div className="drawer-section"><h3>技能要求</h3><div className="tag-list">{skillList.length ? skillList.map((skill) => <span key={skill}>{skill}</span>) : <span>暂无技能标签</span>}</div></div>
          <div className="drawer-section ai-job-section">
            <div className="drawer-section-title"><h3>AI 岗位分析</h3><button onClick={() => onAnalyzeJob(job.job_id)} disabled={aiLoading}><RobotOutlined /> {aiLoading ? "分析中" : "AI 分析"}</button></div>
            {aiLoading && <div className="ai-loading">正在生成岗位分析…</div>}
            {!aiLoading && aiError && <div className="ai-error">{aiError}</div>}
            {!aiLoading && !aiError && <AiStructuredReport content={hasCurrentAi ? aiAnalysis.content : ""} empty="点击 AI 分析生成岗位建议" compact />}
          </div>
          <div className="drawer-section"><h3>岗位信息</h3><dl><div><dt>工作地点</dt><dd>{job.address || job.city}</dd></div><div><dt>行业</dt><dd>{job.industry || "未知"}</dd></div><div><dt>发布时间</dt><dd>{job.publish_time || "未知"}</dd></div><div><dt>招聘状态</dt><dd>{job.recruiter_status || "未知"}</dd></div></dl></div>
        </>}
      </aside>
    </div>
  );
}

export function App() {
  const [scopes, setScopes] = useState([]);
  const [scopeId, setScopeId] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [filterOptions, setFilterOptions] = useState({});
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [jobs, setJobs] = useState({ items: [], pagination: { page: 1, page_size: 10, total: 0, pages: 1 } });
  const [health, setHealth] = useState({ api: false, mysql: false, redis: false });
  const [loading, setLoading] = useState(true);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [aiSummaryOpen, setAiSummaryOpen] = useState(false);
  const [aiSummaryScope, setAiSummaryScope] = useState("");
  const [aiSummary, setAiSummary] = useState({ content: "", generated_at: "", cached: false });
  const [aiSummaryLoading, setAiSummaryLoading] = useState(false);
  const [aiSummaryError, setAiSummaryError] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const [jobAi, setJobAi] = useState({ jobId: "", content: "", loading: false, error: "" });

  useEffect(() => {
    Promise.all([apiGet("/api/scopes"), apiGet("/api/health")])
      .then(([scopeResponse, healthResponse]) => {
        setScopes(scopeResponse.data || []);
        setHealth(healthResponse.data || {});
        if (scopeResponse.data?.length) {
          setScopeId(scopeResponse.data[0].scope_id);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const loadJobs = useCallback((page = 1, currentFilters = appliedFilters) => {
    if (!scopeId) return;
    setJobsLoading(true);
    apiGet("/api/jobs", { scope_id: scopeId, page, page_size: 10, ...currentFilters })
      .then((response) => setJobs(response.data))
      .catch((err) => setError(err.message))
      .finally(() => setJobsLoading(false));
  }, [scopeId, appliedFilters]);

  useEffect(() => {
    if (!scopeId) return;
    setLoading(true); setError("");
    Promise.all([apiGet("/api/dashboard/all", { scope_id: scopeId }), apiGet("/api/filters", { scope_id: scopeId })])
      .then(([dashboardResponse, filtersResponse]) => {
        setDashboard(dashboardResponse.data);
        setFilterOptions(filtersResponse.data || {});
        setFilters(EMPTY_FILTERS); setAppliedFilters(EMPTY_FILTERS);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [scopeId]);

  useEffect(() => { if (scopeId) loadJobs(1, EMPTY_FILTERS); }, [scopeId]);
  useEffect(() => {
    setAiSummaryScope("");
    setAiSummary({ content: "", generated_at: "", cached: false });
    setAiSummaryError("");
    setChatMessages([]);
    setChatError("");
  }, [scopeId]);

  const summary = dataOf(dashboard, "summary") || {};
  const city = dataOf(dashboard, "city") || {};
  const selectedScope = scopes.find((item) => item.scope_id === scopeId);
  const cityRanking = (city.categories || []).map((name, index) => ({ name, count: city.job_counts?.[index] || 0, salary: city.average_salary_wan?.[index] })).slice(0, 10);

  const applySearch = (event) => {
    event.preventDefault();
    setAppliedFilters(filters);
    loadJobs(1, filters);
  };

  const resetFilters = () => {
    setFilters(EMPTY_FILTERS); setAppliedFilters(EMPTY_FILTERS); loadJobs(1, EMPTY_FILTERS);
  };

  const openDetail = (jobId) => {
    setDetail(null); setDetailLoading(true);
    setJobAi({ jobId: "", content: "", loading: false, error: "" });
    apiGet(`/api/jobs/${jobId}`).then((response) => setDetail(response.data)).catch((err) => setError(err.message)).finally(() => setDetailLoading(false));
  };

  const loadAiSummary = () => {
    if (!scopeId) return;
    setAiSummaryOpen(true);
    if (aiSummaryScope === scopeId && aiSummary.content) return;
    setAiSummaryLoading(true); setAiSummaryError("");
    apiGet("/api/ai/summary", { scope_id: scopeId })
      .then((response) => {
        setAiSummaryScope(scopeId);
        setAiSummary(response.data || { content: "", generated_at: "", cached: false });
      })
      .catch((err) => setAiSummaryError(err.message))
      .finally(() => setAiSummaryLoading(false));
  };

  const sendChat = (event) => {
    event.preventDefault();
    const question = chatQuestion.trim();
    if (!scopeId || !question || chatLoading) return;
    setChatQuestion("");
    setChatError("");
    setChatMessages((messages) => [...messages, { role: "user", content: question }]);
    setChatLoading(true);
    apiPost("/api/ai/chat", { scope_id: scopeId, question })
      .then((response) => setChatMessages((messages) => [...messages, { role: "assistant", content: response.data?.answer || "" }]))
      .catch((err) => {
        setChatError(err.message);
        setChatMessages((messages) => [...messages, { role: "assistant", content: err.message, error: true }]);
      })
      .finally(() => setChatLoading(false));
  };

  const analyzeJob = (jobId) => {
    setJobAi({ jobId, content: "", loading: true, error: "" });
    apiGet(`/api/ai/job/${jobId}`)
      .then((response) => setJobAi({ jobId, content: response.data?.content || "", loading: false, error: "" }))
      .catch((err) => setJobAi({ jobId, content: "", loading: false, error: err.message }));
  };

  if (loading && !dashboard) return <div className="app-state"><BarChartOutlined /><h1>正在加载招聘数据</h1><p>正在连接 Flask API、Redis 与 MySQL…</p></div>;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><BarChartOutlined /><strong>高校招聘大数据分析平台</strong></div>
        <nav><a className="active" href="#overview">首页</a><a href="#city-analysis">岗位分析</a><a href="#company-analysis">公司分析</a><a href="#industry-analysis">行业分析</a><a href="#job-list">数据报告</a></nav>
        <div className="top-actions"><label>关键词：<select value={scopeId} onChange={(event) => setScopeId(event.target.value)}>{scopes.map((scope) => <option key={scope.scope_id} value={scope.scope_id}>{scope.keyword}</option>)}</select></label><span><ReloadOutlined /> 数据更新：{summary.data_updated_at || "—"}</span><CalendarOutlined /></div>
      </header>

      <main>
        {error && <div className="error-banner"><span>{error}</span><button onClick={() => window.location.reload()}>重新加载</button></div>}
        <div className="section-heading-row">
          <div className="section-title" id="overview"><i />招聘数据概览 <span>{selectedScope?.keyword || "当前关键词"} · {formatNumber(selectedScope?.job_count)}条明细</span></div>
          <button className="ai-summary-button" onClick={loadAiSummary} disabled={!scopeId || aiSummaryLoading}><RobotOutlined /> {aiSummaryLoading ? "生成中" : "AI 解读"}</button>
        </div>
        <section className="kpi-row">
          <Kpi icon={<CarryOutOutlined />} label="岗位总数" value={formatNumber(summary.job_count)} note="当前关键词" tone="blue" />
          <Kpi icon={<BankOutlined />} label="公司总数" value={formatNumber(summary.company_count)} note="去重公司数量" tone="cyan" />
          <Kpi icon={<EnvironmentOutlined />} label="覆盖城市" value={formatNumber(summary.city_count)} note="数据来源城市" tone="sky" />
          <Kpi icon={<MoneyCollectOutlined />} label="平均年薪" value={summary.average_annual_salary_wan || "—"} suffix="万元" note={`${formatNumber(summary.salary_job_count)}个有效薪资岗位`} tone="green" />
        </section>

        <section className="city-layout" id="city-analysis">
          <Panel title="城市岗位分布" className="city-visual"><CityMap data={city} /></Panel>
          <Panel title="城市洞察 TOP10" className="city-ranking"><ol>{cityRanking.map((item, index) => <li key={item.name}><b>{index + 1}</b><span>{item.name}</span><div><strong>{formatNumber(item.count)}</strong><em>平均年薪 {item.salary ?? "—"}万</em></div></li>)}</ol></Panel>
        </section>

        <section className="distribution-grid" id="company-analysis">
          <Panel title="平均年薪分布（万元）"><PieChart data={dataOf(dashboard, "salary")} centerText="年薪" ariaLabel="平均年薪分布" /></Panel>
          <Panel title="学历要求分布"><PieChart data={dataOf(dashboard, "education")} centerText="学历" ariaLabel="学历要求分布" /></Panel>
          <Panel title="工作经验要求分布"><PieChart data={dataOf(dashboard, "experience")} centerText="经验" ariaLabel="工作经验要求分布" /></Panel>
          <Panel title="公司规模分布"><Chart option={horizontalBarOption(dataOf(dashboard, "company_size"), 8)} ariaLabel="公司规模分布" /></Panel>
          <Panel title="公司类型分布"><PieChart data={dataOf(dashboard, "company_type")} centerText="性质" ariaLabel="公司类型分布" /></Panel>
          <Panel title="融资阶段分布"><PieChart data={dataOf(dashboard, "financing")} centerText="融资" ariaLabel="融资阶段分布" /></Panel>
        </section>

        <section className="analysis-grid" id="industry-analysis">
          <Panel title="近30天岗位发布趋势"><Chart option={trendOption(dataOf(dashboard, "publish_trend"))} ariaLabel="近30天岗位发布趋势" /></Panel>
          <Panel title="技能需求 TOP20"><Chart option={skillsOption(dataOf(dashboard, "skills"))} ariaLabel="技能需求TOP20" /></Panel>
        </section>

        <section className="jobs-section" id="job-list">
          <div className="section-title"><i />岗位列表 <span>共 {formatNumber(jobs.pagination.total)} 条</span></div>
          <form className="job-filters" onSubmit={applySearch}>
            <label className="keyword-input"><SearchOutlined /><input value={filters.keyword} onChange={(event) => setFilters({ ...filters, keyword: event.target.value })} placeholder="请输入关键词（岗位/公司/技能）" /></label>
            <FilterSelect label="城市" value={filters.city} values={filterOptions.cities} onChange={(value) => setFilters({ ...filters, city: value })} />
            <FilterSelect label="工作经验" value={filters.experience} values={filterOptions.experiences} onChange={(value) => setFilters({ ...filters, experience: value })} />
            <FilterSelect label="学历要求" value={filters.education} values={filterOptions.educations} onChange={(value) => setFilters({ ...filters, education: value })} />
            <FilterSelect label="公司规模" value={filters.company_size} values={filterOptions.company_sizes} onChange={(value) => setFilters({ ...filters, company_size: value })} />
            <FilterSelect label="行业" value={filters.industry} values={filterOptions.industries} onChange={(value) => setFilters({ ...filters, industry: value })} />
            <label className="salary-filter"><span>年薪范围（万元）</span><div><input type="number" min="0" step="1" value={filters.salary_min} onChange={(event) => setFilters({ ...filters, salary_min: event.target.value })} placeholder="最低" /><b>–</b><input type="number" min="0" step="1" value={filters.salary_max} onChange={(event) => setFilters({ ...filters, salary_max: event.target.value })} placeholder="最高" /></div></label>
            <button type="button" className="reset-button" onClick={resetFilters}>重置</button><button type="submit" className="search-button"><SearchOutlined /> 搜索</button>
          </form>
          <div className={`table-wrap ${jobsLoading ? "loading" : ""}`}>
            <table><thead><tr><th>职位名称</th><th>公司名称</th><th>城市</th><th>薪资范围</th><th>学历要求</th><th>工作经验</th><th>公司类型</th><th>发布时间</th><th>操作</th></tr></thead>
              <tbody>{jobs.items.length ? jobs.items.map((job) => <tr key={job.job_id}><td>{job.job_name}</td><td>{job.company_name}</td><td>{job.city}</td><td className="salary">{salaryText(job)}</td><td>{job.education || "不限"}</td><td>{job.experience || "不限"}</td><td>{job.company_type || "未知"}</td><td>{job.publish_time}</td><td><button className="detail-link" onClick={() => openDetail(job.job_id)}>查看详情</button></td></tr>) : <tr><td colSpan="9" className="empty-row">没有符合条件的岗位</td></tr>}</tbody></table>
          </div>
          <div className="pagination"><span>第 {jobs.pagination.page} / {jobs.pagination.pages} 页</span><div><button disabled={jobs.pagination.page <= 1} onClick={() => loadJobs(jobs.pagination.page - 1)}>上一页</button>{Array.from({ length: Math.min(5, jobs.pagination.pages) }, (_, index) => { const page = Math.max(1, Math.min(jobs.pagination.pages - 4, jobs.pagination.page - 2)) + index; return <button key={page} className={page === jobs.pagination.page ? "active" : ""} onClick={() => loadJobs(page)}>{page}</button>; })}<button disabled={jobs.pagination.page >= jobs.pagination.pages} onClick={() => loadJobs(jobs.pagination.page + 1)}>下一页</button></div></div>
        </section>

        <section className="secondary-grid">
          <Panel title="企业 TOP15（按岗位数）"><Chart option={horizontalBarOption(dataOf(dashboard, "top_companies"), 15)} ariaLabel="企业岗位数量排名" /></Panel>
          <Panel title="行业分布 TOP15"><Chart option={horizontalBarOption(dataOf(dashboard, "industry"), 15)} ariaLabel="行业岗位数量排名" /></Panel>
        </section>
      </main>

      <footer><span>数据来源：Hive · Spark · MySQL · Redis</span><span className="service-state">Flask API <b className={health.api ? "ok" : "bad"} /> Redis <b className={health.redis ? "ok" : "bad"} /> MySQL <b className={health.mysql ? "ok" : "bad"} /></span></footer>
      <button className={`ai-chat-toggle ${chatOpen ? "active" : ""}`} onClick={() => setChatOpen((value) => !value)}><MessageOutlined /><span>AI 问答</span></button>
      {chatOpen && <section className="ai-chat-panel" aria-label="AI 问答面板">
        <div className="ai-chat-header"><RobotOutlined /><strong>招聘数据 AI 问答</strong><button onClick={() => setChatOpen(false)} aria-label="关闭 AI 问答"><CloseOutlined /></button></div>
        <div className="ai-chat-messages">
          {chatMessages.length ? chatMessages.map((message, index) => <div key={`${message.role}-${index}`} className={`chat-message ${message.role} ${message.error ? "error" : ""}`}><AiText content={message.content} /></div>) : <div className="chat-empty">等待提问</div>}
          {chatLoading && <div className="chat-message assistant"><AiText content="正在分析当前招聘数据…" /></div>}
        </div>
        {chatError && <div className="ai-chat-error">{chatError}</div>}
        <form className="ai-chat-form" onSubmit={sendChat}>
          <input value={chatQuestion} onChange={(event) => setChatQuestion(event.target.value)} maxLength={300} placeholder="输入问题" disabled={chatLoading || !scopeId} />
          <button type="submit" disabled={chatLoading || !scopeId || !chatQuestion.trim()} aria-label="发送问题"><SendOutlined /></button>
        </form>
      </section>}
      <AiSummaryDrawer open={aiSummaryOpen} content={aiSummary.content} loading={aiSummaryLoading} error={aiSummaryError} generatedAt={aiSummary.generated_at} cached={aiSummary.cached} onClose={() => setAiSummaryOpen(false)} />
      <JobDrawer job={detail} loading={detailLoading} onClose={() => { setDetail(null); setDetailLoading(false); }} aiAnalysis={jobAi} aiLoading={jobAi.loading} aiError={jobAi.error} onAnalyzeJob={analyzeJob} />
    </div>
  );
}
