// An in-browser stand-in for the Django API, used only by the shareable demo build (`npm run build:demo`).
// It mirrors the real API's responses and validation rules closely enough for visitors to try every feature
// without a server. Data lives in memory and resets when the page reloads.

const DEMO = { email: "demo@example.com", password: "Demo-password-2026" };
const STATUSES = ["wishlist", "applied", "interviewing", "offer", "rejected", "withdrawn"];
const SUBMITTED = ["applied", "interviewing", "offer", "rejected"];
const RESPONDED = ["interviewing", "offer"];

class MockError extends Error {
  constructor(status, body) {
    super(body.detail ?? "Please check the highlighted fields.");
    this.status = status;
    this.fields = body.detail ? {} : body;
  }
}

const daysAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
};
const now = () => new Date().toISOString();

let nextId = 1;
const id = () => nextId++;
const users = [];
let current = null;

function createUser(email, password, fullName) {
  const user = { id: id(), email, password, full_name: fullName, date_joined: now(), companies: [], applications: [] };
  users.push(user);
  return user;
}

function seedDemo() {
  const user = createUser(DEMO.email, DEMO.password, "Demo User");
  const companies = [
    ["Northwind Analytics", "https://northwind.example.com", "Data", "Remote"],
    ["Blue Harbor Health", "https://blueharbor.example.com", "Healthcare", "Philadelphia, PA"],
    ["Lumen Robotics", "https://lumen.example.com", "Robotics", "New York, NY"],
  ].map(([name, website, industry, location]) => ({ id: id(), name, website, industry, location, created_at: now() }));
  user.companies.push(...companies);
  [
    [0, "Backend Engineer", "interviewing", 110000, 135000, 12, "Second round with the platform team next week."],
    [0, "Data Platform Engineer", "applied", 120000, 145000, 5, ""],
    [1, "Python Developer", "offer", 105000, 125000, 30, "Offer received. Decide by Friday."],
    [1, "API Engineer", "rejected", null, null, 21, ""],
    [2, "ML Infrastructure Engineer", "wishlist", 140000, 170000, null, "Ask a contact about the team first."],
  ].forEach(([c, role_title, status, salary_min, salary_max, ago, notes]) =>
    user.applications.push({
      id: id(),
      company_id: companies[c].id,
      role_title,
      status,
      job_url: "",
      salary_min,
      salary_max,
      applied_on: ago == null ? null : daysAgo(ago),
      notes,
      created_at: new Date(Date.now() - (ago ?? 40) * 864e5).toISOString(),
    }),
  );
}
seedDemo();

const delay = (value) => new Promise((resolve) => setTimeout(() => resolve(value), 120));

function me() {
  if (!current) throw new MockError(401, { detail: "Authentication credentials were not provided." });
  return current;
}

function companyView(user, c) {
  return { ...c, application_count: user.applications.filter((a) => a.company_id === c.id).length };
}

function appView(user, a) {
  const c = user.companies.find((x) => x.id === a.company_id);
  return { ...a, company: { id: c.id, name: c.name, website: c.website } };
}

function validateCompany(user, data, existingId) {
  const errors = {};
  const name = (data.name ?? "").trim();
  if (!name) errors.name = ["This field may not be blank."];
  else if (user.companies.some((c) => c.id !== existingId && c.name.toLowerCase() === name.toLowerCase()))
    errors.name = ["You already have a company with this name."];
  if (data.website && !/^https?:\/\/\S+\.\S+/.test(data.website)) errors.website = ["Enter a valid URL."];
  if (Object.keys(errors).length) throw new MockError(400, errors);
  return { ...data, name };
}

function validateApplication(user, data, existing = {}) {
  const merged = { ...existing, ...data };
  const errors = {};
  if (!user.companies.some((c) => c.id === merged.company_id)) errors.company_id = ["Choose one of your companies."];
  if (!(merged.role_title ?? "").trim()) errors.role_title = ["This field may not be blank."];
  if (!STATUSES.includes(merged.status)) errors.status = ["Choose a valid stage."];
  if (merged.job_url && !/^https?:\/\/\S+\.\S+/.test(merged.job_url)) errors.job_url = ["Enter a valid URL."];
  if (merged.salary_min != null && merged.salary_max != null && merged.salary_min > merged.salary_max)
    errors.salary_min = ["The minimum salary can't be higher than the maximum."];
  if (Object.keys(errors).length) throw new MockError(400, errors);
  return merged;
}

const run = (fn) =>
  delay().then(() => {
    try {
      return fn();
    } catch (err) {
      return Promise.reject(err);
    }
  });

export const mockApi = {
  health: () => Promise.resolve({ status: "ok" }),

  login: (email, password) =>
    run(() => {
      const user = users.find((u) => u.email === email.toLowerCase() && u.password === password);
      if (!user) throw new MockError(401, { detail: "No active account found with the given credentials" });
      current = user;
      return { access: `demo-${user.id}`, refresh: `demo-${user.id}` };
    }),
  register: ({ email, password, full_name }) =>
    run(() => {
      const errors = {};
      const normalized = (email ?? "").trim().toLowerCase();
      if (!/^\S+@\S+\.\S+$/.test(normalized)) errors.email = ["Enter a valid email address."];
      else if (users.some((u) => u.email === normalized)) errors.email = ["An account with this email already exists."];
      if ((password ?? "").length < 8) errors.password = ["This password is too short. It must contain at least 8 characters."];
      if (Object.keys(errors).length) throw new MockError(400, errors);
      const user = createUser(normalized, password, full_name ?? "");
      return { id: user.id, email: user.email, full_name: user.full_name };
    }),
  me: () =>
    run(() => {
      const u = me();
      return { id: u.id, email: u.email, full_name: u.full_name, date_joined: u.date_joined, is_demo: u.email === DEMO.email };
    }),

  listCompanies: () =>
    run(() => {
      const u = me();
      return [...u.companies].sort((a, b) => a.name.localeCompare(b.name)).map((c) => companyView(u, c));
    }),
  createCompany: (data) =>
    run(() => {
      const u = me();
      const company = { id: id(), website: "", industry: "", location: "", ...validateCompany(u, data), created_at: now() };
      u.companies.push(company);
      return companyView(u, company);
    }),
  updateCompany: (companyId, data) =>
    run(() => {
      const u = me();
      const company = u.companies.find((c) => c.id === companyId);
      if (!company) throw new MockError(404, { detail: "Not found." });
      Object.assign(company, validateCompany(u, { ...company, ...data }, companyId));
      return companyView(u, company);
    }),
  deleteCompany: (companyId) =>
    run(() => {
      const u = me();
      u.companies = u.companies.filter((c) => c.id !== companyId);
      u.applications = u.applications.filter((a) => a.company_id !== companyId);
      return null;
    }),

  listApplications: (search = "") =>
    run(() => {
      const u = me();
      const q = search.toLowerCase();
      return u.applications
        .map((a) => appView(u, a))
        .filter((a) => !q || [a.role_title, a.notes, a.company.name].some((t) => t.toLowerCase().includes(q)))
        .sort((a, b) => b.created_at.localeCompare(a.created_at));
    }),
  getApplication: (appId) =>
    run(() => {
      const u = me();
      const app = u.applications.find((a) => a.id === Number(appId));
      if (!app) throw new MockError(404, { detail: "Not found." });
      return appView(u, app);
    }),
  createApplication: (data) =>
    run(() => {
      const u = me();
      const app = { id: id(), ...validateApplication(u, data), created_at: now() };
      u.applications.push(app);
      return appView(u, app);
    }),
  updateApplication: (appId, data) =>
    run(() => {
      const u = me();
      const app = u.applications.find((a) => a.id === Number(appId));
      if (!app) throw new MockError(404, { detail: "Not found." });
      Object.assign(app, validateApplication(u, data, app));
      return appView(u, app);
    }),
  deleteApplication: (appId) =>
    run(() => {
      const u = me();
      u.applications = u.applications.filter((a) => a.id !== Number(appId));
      return null;
    }),
  stats: () =>
    run(() => {
      const u = me();
      const counts = Object.fromEntries(STATUSES.map((s) => [s, 0]));
      u.applications.forEach((a) => counts[a.status]++);
      const submitted = SUBMITTED.reduce((n, s) => n + counts[s], 0);
      const responded = RESPONDED.reduce((n, s) => n + counts[s], 0);
      return {
        total: u.applications.length,
        by_status: STATUSES.map((status) => ({ status, count: counts[status] })),
        response_rate: submitted ? Math.round((responded / submitted) * 1000) / 1000 : 0,
      };
    }),
};
