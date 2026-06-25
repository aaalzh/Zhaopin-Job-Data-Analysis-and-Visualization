async function requestJson(path, options = {}) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => null);
  if (!response.ok || !payload || payload.code !== 0) {
    throw new Error(payload?.message || `请求失败（${response.status}）`);
  }
  return payload;
}

export async function apiGet(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });
  const url = query.size ? `${path}?${query.toString()}` : path;
  return requestJson(url, { headers: { Accept: "application/json" } });
}

export async function apiPost(path, body = {}) {
  return requestJson(path, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
