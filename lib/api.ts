export function getAccessToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) throw new Error("NEXT_PUBLIC_API_BASE_URL is not set");

  const token = getAccessToken();

  const headers = new Headers(init.headers || {});
  headers.set("Content-Type", "application/json");

  // 로그인 후 보호된 API 호출을 위해 자동으로 Bearer 토큰 첨부
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${base}${path}`, {
    ...init,
    headers,
  });

  // 응답 파싱
  const text = await res.text();
  const data = text ? (() => { try { return JSON.parse(text); } catch { return text; } })() : null;

  if (!res.ok) {
    const msg =
      (data && (data.detail || data.message)) ||
      `API Error: ${res.status} ${res.statusText}`;
    throw new Error(msg);
  }

  return data;
}
