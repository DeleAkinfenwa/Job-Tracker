// One function per API call, so components never build URLs themselves.
import { request, requestAll } from "./client.js";
import { mockApi } from "./mock.js";

export const DEMO_CREDENTIALS = { email: "demo@example.com", password: "Demo-password-2026" };

export const STATUSES = [
  { value: "wishlist", label: "Wishlist" },
  { value: "applied", label: "Applied" },
  { value: "interviewing", label: "Interviewing" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

export const statusLabel = (value) => STATUSES.find((s) => s.value === value)?.label ?? value;

const realApi = {
  health: () => request("/health/", { auth: false }),

  login: (email, password) => request("/api/auth/token/", { method: "POST", body: { email, password }, auth: false }),
  register: (data) => request("/api/auth/register/", { method: "POST", body: data, auth: false }),
  me: () => request("/api/auth/me/"),

  listCompanies: () => requestAll("/api/companies/"),
  createCompany: (data) => request("/api/companies/", { method: "POST", body: data }),
  updateCompany: (id, data) => request(`/api/companies/${id}/`, { method: "PATCH", body: data }),
  deleteCompany: (id) => request(`/api/companies/${id}/`, { method: "DELETE" }),

  // Filtering and sorting happen in the API, e.g. ?status=applied&ordering=-salary_max
  listApplications: ({ search = "", status = "", ordering = "" } = {}) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    if (ordering) params.set("ordering", ordering);
    const query = params.toString();
    return requestAll(`/api/applications/${query ? `?${query}` : ""}`);
  },
  getApplication: (id) => request(`/api/applications/${id}/`),
  createApplication: (data) => request("/api/applications/", { method: "POST", body: data }),
  updateApplication: (id, data) => request(`/api/applications/${id}/`, { method: "PATCH", body: data }),
  deleteApplication: (id) => request(`/api/applications/${id}/`, { method: "DELETE" }),
  stats: () => request("/api/applications/stats/"),
};

// The shareable demo build swaps in an in-browser copy of the API, so it works without a server.
export const IS_STANDALONE_DEMO = import.meta.env.VITE_STANDALONE_DEMO === "true";
export const api = IS_STANDALONE_DEMO ? mockApi : realApi;
