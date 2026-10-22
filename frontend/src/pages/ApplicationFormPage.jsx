import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, STATUSES } from "../api/endpoints.js";
import ConfirmButton from "../components/ConfirmButton.jsx";
import Field from "../components/Field.jsx";

const NEW_COMPANY = "new";

const EMPTY = {
  company_id: "",
  new_company: "",
  role_title: "",
  status: "applied",
  job_url: "",
  salary_min: "",
  salary_max: "",
  applied_on: "",
  notes: "",
};

// The form keeps everything as text; the API wants numbers and nulls for empty optional fields.
function toPayload(form, companyId) {
  const numberOrNull = (v) => (v === "" ? null : Number(v));
  return {
    company_id: Number(companyId),
    role_title: form.role_title,
    status: form.status,
    job_url: form.job_url,
    salary_min: numberOrNull(form.salary_min),
    salary_max: numberOrNull(form.salary_max),
    applied_on: form.applied_on || null,
    notes: form.notes,
  };
}

function fromApplication(app) {
  return {
    ...EMPTY,
    company_id: String(app.company.id),
    role_title: app.role_title,
    status: app.status,
    job_url: app.job_url,
    salary_min: app.salary_min ?? "",
    salary_max: app.salary_max ?? "",
    applied_on: app.applied_on ?? "",
    notes: app.notes,
  };
}

export default function ApplicationFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [companies, setCompanies] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api.listCompanies(), isEdit ? api.getApplication(id) : null])
      .then(([companyList, app]) => {
        setCompanies(companyList);
        if (app) setForm(fromApplication(app));
        else setForm((f) => ({ ...f, company_id: companyList.length ? String(companyList[0].id) : NEW_COMPANY }));
      })
      .catch((err) => setMessage(err.status === 404 ? "This application doesn't exist." : err.message));
  }, [id, isEdit]);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setMessage(null);
    try {
      let companyId = form.company_id;
      if (companyId === NEW_COMPANY) {
        try {
          const company = await api.createCompany({ name: form.new_company });
          companyId = String(company.id);
          // Remember it, so a second submit after a validation error doesn't create it again.
          setCompanies((list) => [...list, company]);
          setForm((f) => ({ ...f, company_id: companyId }));
        } catch (err) {
          setErrors({ new_company: err.fields.name ?? [err.message] });
          return;
        }
      }
      const payload = toPayload(form, companyId);
      if (isEdit) await api.updateApplication(id, payload);
      else await api.createApplication(payload);
      navigate("/");
    } catch (err) {
      setErrors(err.fields);
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    try {
      await api.deleteApplication(id);
      navigate("/");
    } catch (err) {
      setMessage(err.message);
    }
  }

  if (companies === null) return <p className="page-message">{message ?? "Loading…"}</p>;

  return (
    <div className="form-page">
      <Link to="/" className="back-link">
        ← Back to applications
      </Link>
      <h1>{isEdit ? "Edit application" : "Add an application"}</h1>

      <form className="card form-card" onSubmit={onSubmit}>
        <div className="grid-2">
          <Field label="Company" name="company_id" as="select" value={form.company_id} onChange={onChange} errors={errors}>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
            <option value={NEW_COMPANY}>+ Add a new company</option>
          </Field>
          {form.company_id === NEW_COMPANY ? (
            <Field
              label="New company name"
              name="new_company"
              required
              value={form.new_company}
              onChange={onChange}
              errors={errors}
            />
          ) : (
            <div />
          )}
        </div>

        <div className="grid-2">
          <Field label="Job title" name="role_title" required value={form.role_title} onChange={onChange} errors={errors} />
          <Field label="Stage" name="status" as="select" value={form.status} onChange={onChange} errors={errors}>
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </Field>
        </div>

        <div className="grid-2">
          <Field
            label="Salary from (USD per year)"
            name="salary_min"
            type="number"
            min="0"
            step="1000"
            value={form.salary_min}
            onChange={onChange}
            errors={errors}
          />
          <Field
            label="Salary to (USD per year)"
            name="salary_max"
            type="number"
            min="0"
            step="1000"
            value={form.salary_max}
            onChange={onChange}
            errors={errors}
          />
        </div>

        <div className="grid-2">
          <Field label="Date applied" name="applied_on" type="date" value={form.applied_on} onChange={onChange} errors={errors} />
          <Field
            label="Link to the job posting"
            name="job_url"
            type="url"
            placeholder="https://"
            value={form.job_url}
            onChange={onChange}
            errors={errors}
          />
        </div>

        <Field label="Notes" name="notes" as="textarea" rows="4" value={form.notes} onChange={onChange} errors={errors} />

        {message && (
          <p className="form-error" role="alert">
            {message}
          </p>
        )}

        <div className="form-actions">
          {isEdit && (
            <ConfirmButton question="Delete this application?" onConfirm={onDelete} />
          )}
          <span className="spacer" />
          <Link to="/" className="btn btn-ghost">
            Cancel
          </Link>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Saving…" : isEdit ? "Save changes" : "Add application"}
          </button>
        </div>
      </form>
    </div>
  );
}
