// A small wrapper around fetch that talks to the Django API.
// It adds the login token to each request, and when the short-lived access token
// expires it quietly swaps the refresh token for a new one and retries once.

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

const ACCESS_KEY = "jobtracker.access";
const REFRESH_KEY = "jobtracker.refresh";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  save({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

/** An error from the API. `fields` holds per-field messages, e.g. { name: ["This field is required."] }. */
export class ApiError extends Error {
  constructor(status, body) {
    super(messageFrom(body) || `Request failed (${status})`);
    this.status = status;
    this.fields = body && typeof body === "object" && !body.detail ? body : {};
  }
}

function messageFrom(body) {
  if (!body || typeof body !== "object") return null;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.non_field_errors)) return body.non_field_errors.join(" ");
  return "Please check the highlighted fields.";
}

// Called when the session can't be recovered, so the app can send the user back to the login page.
let onSessionExpired = () => {};
export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler;
}

let refreshing = null;
async function refreshAccessToken() {
  // If several requests fail at once, they all wait for the same refresh.
  refreshing ??= fetch(`${API_URL}/api/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokens.refresh }),
  })
    .then(async (res) => {
      if (!res.ok) return false;
      tokens.save(await res.json());
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function request(path, { method = "GET", body, auth = true, retry = true } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (res.status === 401 && auth && retry && tokens.refresh) {
    if (await refreshAccessToken()) return request(path, { method, body, auth, retry: false });
    tokens.clear();
    onSessionExpired();
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

/** Fetch every page of a paginated list (the API returns at most 100 per page). */
export async function requestAll(path) {
  const sep = path.includes("?") ? "&" : "?";
  let page = await request(`${path}${sep}limit=100`);
  const results = [...page.results];
  while (page.next) {
    const next = new URL(page.next);
    page = await request(next.pathname + next.search);
    results.push(...page.results);
  }
  return results;
}
