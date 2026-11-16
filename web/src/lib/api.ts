// Backend API mijozi. Tokenlar brauzer xotirasida (localStorage) saqlanadi.
// Eslatma: serverga chiqarishda xavfsizroq usulga (httpOnly cookie) o'tkaziladi.

const ACCESS = "colba.access";
const REFRESH = "colba.refresh";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const tokens = {
  get access() {
    return typeof window === "undefined" ? null : localStorage.getItem(ACCESS);
  },
  get refresh() {
    return typeof window === "undefined" ? null : localStorage.getItem(REFRESH);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

function errorMessage(data: unknown, status: number): string {
  if (status === 404) return "Topilmadi.";
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.detail === "string") return d.detail;
    const first = Object.entries(d)[0];
    if (first) {
      const [field, val] = first;
      const msg = Array.isArray(val) ? val[0] : val;
      return `${field}: ${String(msg)}`;
    }
  }
  if (status === 403) return "Bu amal uchun ruxsatingiz yo'q.";
  if (status >= 500) return "Serverda xatolik. Birozdan keyin qayta urinib ko'ring.";
  return `Xatolik (${status})`;
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const refresh = tokens.refresh;
  if (!refresh) return false;
  refreshing ??= (async () => {
    try {
      const r = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });
      if (!r.ok) return false;
      const data = await r.json();
      tokens.set(data.access, data.refresh);
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => (refreshing = null), 0);
    }
  })();
  return refreshing;
}

/** path: "zakovat/games/2/sheet" (boshida va oxirida "/" siz). */
export async function api<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown; query?: Record<string, string> } = {},
  retry = true,
): Promise<T> {
  const qs = opts.query ? "?" + new URLSearchParams(opts.query).toString() : "";
  const headers: Record<string, string> = { Accept: "application/json" };
  const access = tokens.access;
  if (access) headers.Authorization = `Bearer ${access}`;
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) body = opts.body;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(`/api/${path}${qs}`, { method: opts.method ?? "GET", headers, body });
  if (res.status === 401 && retry && (await tryRefresh())) {
    return api<T>(path, opts, false);
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, errorMessage(data, res.status));
  return data as T;
}
