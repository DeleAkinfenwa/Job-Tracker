import { useEffect, useState } from "react";

import { api } from "../api/endpoints.js";
import Field from "../components/Field.jsx";

const EMPTY = { name: "", website: "", industry: "", location: "" };

function CompanyForm({ initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial ?? EMPTY);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const isEdit = Boolean(initial?.id);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      const data = { name: form.name, website: form.website, industry: form.industry, location: form.location };
      await (isEdit ? api.updateCompany(initial.id, data) : api.createCompany(data));
      setForm(EMPTY);
      onSaved();
    } catch (err) {
      setErrors(Object.keys(err.fields).length ? err.fields : { name: [err.message] });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form-card" onSubmit={onSubmit}>
      <h2>{isEdit ? `Edit ${initial.name}` : "Add a company"}</h2>
      <div className="grid-2">
        <Field label="Name" name="name" required value={form.name} onChange={onChange} errors={errors} />
        <Field
          label="Website"
          name="website"
          type="url"
          placeholder="https://"
          value={form.website}
          onChange={onChange}
          errors={errors}
        />
        <Field label="Industry" name="industry" value={form.industry} onChange={onChange} errors={errors} />
        <Field label="Location" name="location" value={form.location} onChange={onChange} errors={errors} />
      </div>
      <div className="form-actions">
        <span className="spacer" />
        {isEdit && (
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Saving…" : isEdit ? "Save changes" : "Add company"}
        </button>
      </div>
    </form>
  );
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState(null);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);

  const load = () =>
    api
      .listCompanies()
      .then(setCompanies)
      .catch((err) => setError(err.message));

  useEffect(() => {
    load();
  }, []);

  async function onDelete(company) {
    const extra = company.application_count
      ? ` Its ${company.application_count} application(s) will be deleted too.`
      : "";
    if (!window.confirm(`Delete ${company.name}?${extra}`)) return;
    try {
      await api.deleteCompany(company.id);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Companies</h1>
      </div>

      <CompanyForm
        key={editing?.id ?? "new"}
        initial={editing}
        onSaved={() => {
          setEditing(null);
          load();
        }}
        onCancel={() => setEditing(null)}
      />

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {companies === null ? (
        <p className="page-message">Loading companies…</p>
      ) : companies.length === 0 ? (
        <p className="page-message">No companies yet. Add one above.</p>
      ) : (
        <ul className="company-list">
          {companies.map((c) => (
            <li key={c.id} className="card company">
              <div className="company-main">
                <div className="company-name">
                  {c.website ? (
                    <a href={c.website} target="_blank" rel="noreferrer">
                      {c.name}
                    </a>
                  ) : (
                    c.name
                  )}
                </div>
                <div className="muted">{[c.industry, c.location].filter(Boolean).join(" · ") || "No details yet"}</div>
              </div>
              <div className="company-count">
                {c.application_count} application{c.application_count === 1 ? "" : "s"}
              </div>
              <div className="company-actions">
                <button type="button" className="btn btn-ghost" onClick={() => {
                    setEditing(c);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  Edit
                </button>
                <button type="button" className="btn btn-ghost danger-text" onClick={() => onDelete(c)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
