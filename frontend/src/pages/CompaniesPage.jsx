import { useEffect, useState } from "react";

import { api } from "../api/endpoints.js";
import ConfirmButton from "../components/ConfirmButton.jsx";
import Field from "../components/Field.jsx";

// A blank company form.
const EMPTY = { name: "", website: "", industry: "", location: "" };

// One form for both adding a new company and editing an existing one.
function CompanyForm({ initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial ?? EMPTY);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const isEdit = Boolean(initial?.id);

  // Keep the form state in sync with whatever the user types.
  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  // Save the company, then clear the form and tell the page to reload the list.
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

// The companies page: the add/edit form above a list of saved companies.
export default function CompaniesPage() {
  const [companies, setCompanies] = useState(null);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);

  // Fetch the company list from the API.
  const load = () =>
    api
      .listCompanies()
      .then(setCompanies)
      .catch((err) => setError(err.message));

  useEffect(() => {
    load();
  }, []);

  // Delete a company (and its applications), then reload the list.
  async function onDelete(company) {
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

      {/* The key resets the form whenever a different company is picked for editing. */}
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

      {/* Loading message, empty state, or one card per company. */}
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
              {/* Edit scrolls up to the form; delete asks to confirm first. */}
              <div className="company-actions">
                <button type="button" className="btn btn-ghost" onClick={() => {
                    setEditing(c);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  Edit
                </button>
                <ConfirmButton
                  className="btn btn-ghost danger-text"
                  question={
                    c.application_count
                      ? `Also deletes ${c.application_count} application${c.application_count === 1 ? "" : "s"}.`
                      : "Delete this company?"
                  }
                  onConfirm={() => onDelete(c)}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
