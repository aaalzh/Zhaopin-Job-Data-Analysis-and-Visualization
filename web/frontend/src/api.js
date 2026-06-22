export async function apiGet(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });
  const url = query.size ? `${path}?${query.toString()}` : path;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  const payload = await response.json().catch(() => null);
  if (!response.ok || !payload || payload.code !== 0) {
    throw new Error(payload?.message || `请求失败（${response.status}）`);
  }
  return payload;
}
