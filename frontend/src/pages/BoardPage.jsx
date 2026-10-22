import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, STATUSES } from "../api/endpoints.js";
import StatsBar from "../components/StatsBar.jsx";
import { formatDate, formatSalary } from "../format.js";

function ApplicationCard({ app, onStatusChange }) {
  const salary = formatSalary(app.salary_min, app.salary_max);
  const applied = formatDate(app.applied_on);

  return (
    <article className="app-card">
      <Link to={`/applications/${app.id}`} className="app-card-title">
        {app.role_title}
      </Link>
      <div className="app-card-company">{app.company.name}</div>
      {salary && <div className="app-card-meta">{salary}</div>}
      {applied && <div className="app-card-meta">Applied {applied}</div>}
      <label className="sr-only" htmlFor={`status-${app.id}`}>
        Stage for {app.role_title}
      </label>
      <select
        id={`status-${app.id}`}
        className="app-card-status"
        value={app.status}
        onChange={(e) => onStatusChange(app, e.target.value)}
      >
        {STATUSES.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
    </article>
  );
}

export default function BoardPage() {
  const [apps, setApps] = useState(null);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState(null);

  const loadStats = useCallback(() => api.stats().then(setStats), []);

  useEffect(() => {
    // Wait until the user stops typing before searching.
    const timer = setTimeout(() => {
      api
        .listApplications(search.trim())
        .then(setApps)
        .catch((err) => setError(err.message));
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    loadStats().catch(() => {});
  }, [loadStats]);

  async function changeStatus(app, status) {
    const previous = apps;
    // Update the screen straight away, and undo it if the save fails.
    setApps(apps.map((a) => (a.id === app.id ? { ...a, status } : a)));
    try {
      await api.updateApplication(app.id, { status });
      loadStats();
    } catch (err) {
      setApps(previous);
      setError(err.message);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Applications</h1>
        <Link to="/applications/new" className="btn btn-primary">
          + Add application
        </Link>
      </div>

      <StatsBar stats={stats} />

      <input
        type="search"
        className="search"
        placeholder="Search by role, company or notes"
        aria-label="Search applications"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {apps === null ? (
        <p className="page-message">Loading applications…</p>
      ) : apps.length === 0 && !search ? (
        <div className="empty card">
          <h2>No applications yet</h2>
          <p className="muted">Add a company you're interested in, then log the roles you apply for.</p>
          <Link to="/applications/new" className="btn btn-primary">
            Add your first application
          </Link>
        </div>
      ) : (
        <div className="board">
          {STATUSES.map((column) => {
            const items = apps.filter((a) => a.status === column.value);
            return (
              <section key={column.value} className={`column column-${column.value}`} aria-label={column.label}>
                <h2 className="column-title">
                  {column.label} <span className="count">{items.length}</span>
                </h2>
                {items.map((app) => (
                  <ApplicationCard key={app.id} app={app} onStatusChange={changeStatus} />
                ))}
                {items.length === 0 && <p className="column-empty">Nothing here</p>}
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}
