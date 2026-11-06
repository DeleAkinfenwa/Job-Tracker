// One function per API call, so components never build URLs themselves.
import { request, requestAll } from "./client.js";
import { mockApi } from "./mock.js";

// The demo account's login, used by the "Explore the demo" button.
export const DEMO_CREDENTIALS = { email: "demo@example.com", password: "Demo-password-2026" };

// Every stage an application can be in, in pipeline order.
export const STATUSES = [
  { value: "wishlist", label: "Wishlist" },
  { value: "applied", label: "Applied" },
  { value: "interviewing", label: "Interviewing" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

// Turns a stage value like "interviewing" into its display label.
export const statusLabel = (value) => STATUSES.find((s) => s.value === value)?.label ?? value;

// Calls to the real Django API.
const realApi = {
  // Public check that the server is up.
  health: () => request("/health/", { auth: false }),

  // Accounts: log in, sign up, and fetch the current user.
  login: (email, password) => request("/api/auth/token/", { method: "POST", body: { email, password }, auth: false }),
  register: (data) => request("/api/auth/register/", { method: "POST", body: data, auth: false }),
  me: () => request("/api/auth/me/"),

  // Companies: list, create, edit and delete.
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
  // Single applications, plus the numbers for the summary panel.
  getApplication: (id) => request(`/api/applications/${id}/`),
  createApplication: (data) => request("/api/applications/", { method: "POST", body: data }),
  updateApplication: (id, data) => request(`/api/applications/${id}/`, { method: "PATCH", body: data }),
  deleteApplication: (id) => request(`/api/applications/${id}/`, { method: "DELETE" }),
  stats: () => request("/api/applications/stats/"),

  // Resume agent (only works for the account set in AGENT_OWNER_EMAILS on the server).
  agentStatus: () => request("/api/agent/status/"),
  agentProfile: () => request("/api/agent/profile/"),
  saveAgentProfile: (yaml) => request("/api/agent/profile/", { method: "PUT", body: { yaml } }),
  listEntries: () => request("/api/agent/entries/"),
  logEntry: (data) => request("/api/agent/entries/", { method: "POST", body: data }),
  updateEntry: (id, data) => request(`/api/agent/entries/${id}/`, { method: "PATCH", body: data }),
  deleteEntry: (id) => request(`/api/agent/entries/${id}/`, { method: "DELETE" }),
  importProfileBullets: () => request("/api/agent/entries/import_profile/", { method: "POST" }),
  importEntries: (entries, replace) =>
    request("/api/agent/entries/import_json/", { method: "POST", body: { entries, replace } }),
  listRuns: () => requestAll("/api/agent/runs/"),
  getRun: (id) => request(`/api/agent/runs/${id}/`),
  checkFit: (data) => request("/api/agent/runs/evaluate/", { method: "POST", body: data }),
  tailorResume: (data) => request("/api/agent/runs/tailor/", { method: "POST", body: data }),
  resumeText: (id) => request(`/api/agent/runs/${id}/text/`),
  resumeDocx: (id) => request(`/api/agent/runs/${id}/docx/`, { blob: true }),
};

// The shareable demo build swaps in an in-browser copy of the API, so it works without a server.
export const IS_STANDALONE_DEMO = import.meta.env.VITE_STANDALONE_DEMO === "true";
export const api = IS_STANDALONE_DEMO ? mockApi : realApi;
