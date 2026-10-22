import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, STATUSES, statusLabel } from "../api/endpoints.js";
import PipelineSummary from "../components/PipelineSummary.jsx";
import { formatDate, formatSalary, timeAgo } from "../format.js";

// Columns that can be sorted, and the API field each one sorts by.
const SORTABLE = {
  role: { label: "Role", field: "role_title", firstDirection: "" },
  salary: { label: "Salary", field: "salary_max", firstDirection: "-" },
  applied: { label: "Applied", field: "applied_on", firstDirection: "-" },
  added: { label: "Added", field: "created_at", firstDirection: "-" },
};

function SortHeader({ column, ordering, onSort }) {
  const { label, field, firstDirection } = SORTABLE[column];
  const current = ordering.replace(/^-/, "") === field ? (ordering.startsWith("-") ? "descending" : "ascending") : "none";
  const next = current === "none" ? `${firstDirection}${field}` : current === "descending" ? field : `-${field}`;

  return (
    <th aria-sort={current} scope="col">
      <button type="button" className="sort-button" onClick={() => onSort(next)}>
        {label}
        <span className="sort-arrow" aria-hidden="true">
          {current === "ascending" ? "↑" : current === "descending" ? "↓" : "↕"}
        </span>
      </button>
    </th>
  );
}

export default function ApplicationsPage() {
  const navigate = useNavigate();
  const [apps, setApps] = useState(null);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [error, setError] = useState(null);

  const loadStats = useCallback(() => api.stats().then(setStats), []);

  useEffect(() => {
    // Wait until the user stops typing before asking the API.
    const timer = setTimeout(() => {
      api
        .listApplications({ search: search.trim(), status, ordering })
        .then(setApps)
        .catch((err) => setError(err.message));
    }, 200);
    return () => clearTimeout(timer);
  }, [search, status, ordering]);

  useEffect(() => {
    loadStats().catch(() => {});
  }, [loadStats]);

  async function changeStatus(app, newStatus) {
    const previous = apps;
    setApps(apps.map((a) => (a.id === app.id ? { ...a, status: newStatus, updated_at: new Date().toISOString() } : a)));
    try {
      await api.updateApplication(app.id, { status: newStatus });
      loadStats();
    } catch (err) {
      setApps(previous);
      setError(err.message);
    }
  }

  const filtering = Boolean(search || status);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Applications</h1>
          <p className="muted page-subtitle">Every role you're tracking. Click a role to see or edit it.</p>
        </div>
        <Link to="/applications/new" className="btn btn-primary">
          + Add application
        </Link>
      </div>

      <PipelineSummary stats={stats} activeStatus={status} onSelect={setStatus} />

      <div className="toolbar">
        <input
          type="search"
          id="search"
          className="search"
          placeholder="Search roles, companies and notes"
          aria-label="Search applications"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label className="toolbar-select">
          <span>Stage</span>
          <select id="stage-filter" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All stages</option>
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="toolbar-select sort-select">
          <span>Sort</span>
          <select id="sort" value={ordering} onChange={(e) => setOrdering(e.target.value)}>
            <option value="-created_at">Newest first</option>
            <option value="-applied_on">Recently applied</option>
            <option value="-salary_max">Highest salary</option>
            <option value="role_title">Role A to Z</option>
          </select>
        </label>
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {apps === null ? (
        <p className="page-message">Loading applications…</p>
      ) : apps.length === 0 ? (
        <div className="empty card">
          {filtering ? (
            <>
              <h2>No matches</h2>
              <p className="muted">Nothing matches {status ? `the ${statusLabel(status)} stage` : "your search"}.</p>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setSearch("");
                  setStatus("");
                }}
              >
                Clear filters
              </button>
            </>
          ) : (
            <>
              <h2>No applications yet</h2>
              <p className="muted">Add a company you're interested in, then log the roles you apply for.</p>
              <Link to="/applications/new" className="btn btn-primary">
                Add your first application
              </Link>
            </>
          )}
        </div>
      ) : (
        <div className="table-wrap card">
          <table className="apps-table">
            <thead>
              <tr>
                <SortHeader column="role" ordering={ordering} onSort={setOrdering} />
                <th scope="col">Stage</th>
                <SortHeader column="salary" ordering={ordering} onSort={setOrdering} />
                <SortHeader column="applied" ordering={ordering} onSort={setOrdering} />
                <th scope="col">Last update</th>
              </tr>
            </thead>
            <tbody>
              {apps.map((app) => (
                <tr key={app.id} onClick={(e) => e.target.closest("select, a") || navigate(`/applications/${app.id}`)}>
                  <td className="cell-role">
                    <div className="role-stack">
                      <Link to={`/applications/${app.id}`} className="role-link">
                        {app.role_title}
                      </Link>
                      <span className="company-name-small">{app.company.name}</span>
                    </div>
                  </td>
                  <td data-label="Stage">
                    <label className="sr-only" htmlFor={`status-${app.id}`}>
                      Stage for {app.role_title}
                    </label>
                    <select
                      id={`status-${app.id}`}
                      className={`stage-pill stage-${app.status}`}
                      value={app.status}
                      onChange={(e) => changeStatus(app, e.target.value)}
                    >
                      {STATUSES.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td data-label="Salary" className="num">
                    {formatSalary(app.salary_min, app.salary_max) ?? <span className="muted">Not listed</span>}
                  </td>
                  <td data-label="Applied" className="num">
                    {formatDate(app.applied_on) ?? <span className="muted">Not yet</span>}
                  </td>
                  <td data-label="Last update" className="muted">
                    {timeAgo(app.updated_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
