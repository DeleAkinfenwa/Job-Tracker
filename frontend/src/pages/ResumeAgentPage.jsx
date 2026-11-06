import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/endpoints.js";
import ConfirmButton from "../components/ConfirmButton.jsx";
import Field from "../components/Field.jsx";

const TABS = [
  { key: "tailor", label: "Tailor a resume" },
  { key: "log", label: "Career log" },
  { key: "profile", label: "Profile" },
];

const today = () => new Date().toISOString().slice(0, 10);

// A short list with a heading, or nothing when it's empty.
function ListBlock({ title, items, empty }) {
  if (!items?.length && !empty) return null;
  return (
    <div className="agent-block">
      <h3>{title}</h3>
      {items?.length ? (
        <ul>
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">{empty}</p>
      )}
    </div>
  );
}

// The fit score as a coloured badge.
function Score({ value }) {
  const n = Number(value);
  const band = !Number.isFinite(n) ? "" : n >= 7 ? "hi" : n >= 5 ? "mid" : "lo";
  return (
    <span className={`fit-score ${band}`} aria-label={`Fit ${Number.isFinite(n) ? n : "unknown"} out of 10`}>
      {Number.isFinite(n) ? n : "?"}
      <small>/10</small>
    </span>
  );
}

// What came back from a fit check or a tailored resume.
function RunResult({ run, roles = [] }) {
  const [copied, setCopied] = useState("");
  const [error, setError] = useState(null);
  const r = run.result || {};
  const isResume = run.kind === "tailor";

  async function download() {
    setError(null);
    try {
      const blob = await api.resumeDocx(run.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${run.job_title || "Resume"}.docx`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err.message);
    }
  }

  async function copy() {
    setError(null);
    try {
      const { text } = await api.resumeText(run.id);
      await navigator.clipboard.writeText(text);
      setCopied("Copied.");
    } catch {
      setError("Couldn't copy. Download the Word file instead.");
    }
  }

  if (!run.ok) {
    return (
      <div className="card agent-result">
        <p className="danger-text">This run didn't finish: {run.error || "unknown problem"}</p>
      </div>
    );
  }

  return (
    <div className="card agent-result" aria-live="polite">
      <div className="agent-result-head">
        <Score value={r.fit_score} />
        <div>
          <h2>{run.job_title || (isResume ? "Tailored resume" : "Fit check")}</h2>
          {r.worth_applying && <p className="muted">Worth applying: {r.worth_applying}</p>}
          <p>{r.fit_explanation}</p>
        </div>
      </div>

      {isResume && (
        <>
          <div className="form-actions">
            <button type="button" className="btn btn-primary" onClick={download}>
              Download Word file
            </button>
            <button type="button" className="btn" onClick={copy}>
              Copy as text
            </button>
            <span className="muted">{copied}</span>
          </div>
          {error && <p className="form-error">{error}</p>}

          <div className="agent-block">
            <h3>Summary</h3>
            <p>{r.summary}</p>
          </div>
          {r.skills?.length > 0 && (
            <div className="agent-block">
              <h3>Skills</h3>
              {r.skills.map((g) => (
                <p key={g.category}>
                  <strong>{g.category}:</strong> {g.items.join(", ")}
                </p>
              ))}
            </div>
          )}
          <div className="agent-block">
            <h3>Experience bullets</h3>
            {r.experience?.map((role) => (
              <div key={role.role_key}>
                <p className="muted">{roles.find((r) => r.key === role.role_key)?.company ?? role.role_key}</p>
                <ul>
                  {role.bullets.map((b, i) => (
                    <li key={i}>
                      {b.text} <span className="muted">(log entries {b.sources.join(", ")})</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <ListBlock title="Removed by the accuracy check" items={r.removed} empty="Nothing was removed." />
          <ListBlock title="Keywords missing" items={r.keywords_missing} />
          <ListBlock title="Gaps (left off on purpose)" items={r.gaps} />
          <ListBlock title="Be ready to explain in an interview" items={r.interview_prep} />
        </>
      )}

      {!isResume && (
        <>
          <ListBlock title="Strengths" items={r.strengths} />
          <ListBlock title="Gaps" items={r.gaps} />
          <ListBlock title="Possible blockers" items={r.hard_blockers} />
          <ListBlock title="Keywords missing" items={r.keywords_missing} />
        </>
      )}
    </div>
  );
}

// Paste a posting, then check the fit or build a resume. Past runs are listed underneath.
function TailorTab({ roles, onUsage }) {
  const [params] = useSearchParams();
  const [applications, setApplications] = useState([]);
  const [form, setForm] = useState({ application_id: params.get("application") || "", job_title: "", job_text: "" });
  const [runs, setRuns] = useState([]);
  const [current, setCurrent] = useState(null);
  const [busy, setBusy] = useState("");
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);

  const loadRuns = useCallback(() => api.listRuns().then(setRuns).catch(() => {}), []);
  useEffect(() => {
    api.listApplications().then(setApplications).catch(() => {});
    loadRuns();
  }, [loadRuns]);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function start(kind) {
    setBusy(kind);
    setErrors({});
    setMessage(null);
    try {
      const body = {
        job_text: form.job_text,
        job_title: form.job_title,
        application_id: form.application_id ? Number(form.application_id) : null,
      };
      const run = await (kind === "tailor" ? api.tailorResume(body) : api.checkFit(body));
      setCurrent(run);
      loadRuns();
    } catch (err) {
      setErrors(err.fields);
      setMessage(err.message);
    } finally {
      setBusy("");
      onUsage();
    }
  }

  async function open(id) {
    setMessage(null);
    try {
      setCurrent(await api.getRun(id));
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <>
      <form className="card form-card" onSubmit={(e) => e.preventDefault()}>
        <div className="grid-2">
          <Field
            label="For which application? (optional)"
            name="application_id"
            as="select"
            value={form.application_id}
            onChange={onChange}
            errors={errors}
          >
            <option value="">Not linked</option>
            {applications.map((a) => (
              <option key={a.id} value={a.id}>
                {a.role_title} at {a.company.name}
              </option>
            ))}
          </Field>
          <Field
            label="Job name (optional)"
            name="job_title"
            placeholder="Taken from the application if left empty"
            value={form.job_title}
            onChange={onChange}
            errors={errors}
          />
        </div>
        <Field
          label="Job posting"
          name="job_text"
          as="textarea"
          rows="10"
          required
          placeholder="Paste the whole posting: title, duties and requirements."
          value={form.job_text}
          onChange={onChange}
          errors={errors}
        />
        {message && (
          <p className="form-error" role="alert">
            {message}
          </p>
        )}
        <div className="form-actions">
          <span className="muted">Each button press is one AI run. A resume takes about a minute.</span>
          <span className="spacer" />
          <button type="button" className="btn" disabled={Boolean(busy) || !form.job_text.trim()} onClick={() => start("evaluate")}>
            {busy === "evaluate" ? "Checking…" : "Check fit"}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={Boolean(busy) || !form.job_text.trim()}
            onClick={() => start("tailor")}
          >
            {busy === "tailor" ? (
              <>
                <span className="spinner" aria-hidden="true" /> Writing and checking…
              </>
            ) : (
              "Build resume"
            )}
          </button>
        </div>
      </form>

      {current && <RunResult run={current} roles={roles} />}

      {runs.length > 0 && (
        <div className="card form-card">
          <h2>Earlier runs</h2>
          <ul className="run-list">
            {runs.map((run) => (
              <li key={run.id}>
                <button type="button" className="btn btn-ghost" onClick={() => open(run.id)}>
                  {run.kind === "tailor" ? "Resume" : "Fit check"}: {run.job_title || "Untitled job"}
                </button>
                <span className="muted">
                  {run.ok ? (run.fit_score != null ? `${run.fit_score}/10` : "") : "failed"} ·{" "}
                  {new Date(run.created_at).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

// Everything you've done at work, in your own words. Resume bullets must cite these.
function LogTab({ roles, onUsage }) {
  const [entries, setEntries] = useState(null);
  const [form, setForm] = useState({ role: "", entry_date: today(), raw_text: "", use_ai: false });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [importText, setImportText] = useState("");

  const load = useCallback(() => api.listEntries().then(setEntries).catch((err) => setMessage(err.message)), []);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (!form.role && roles.length) setForm((f) => ({ ...f, role: roles[0].key }));
  }, [roles, form.role]);

  const onChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setMessage(null);
    try {
      const entry = await api.logEntry(form);
      setForm({ ...form, raw_text: "" });
      setMessage(
        entry.open_questions?.length
          ? `Saved entry #${entry.id}. To make it stronger, log a follow-up that answers: ${entry.open_questions.join(" ")}`
          : `Saved entry #${entry.id}.`,
      );
      load();
    } catch (err) {
      setErrors(err.fields);
      setMessage(err.message);
    } finally {
      setBusy(false);
      if (form.use_ai) onUsage();
    }
  }

  async function importBullets() {
    setMessage(null);
    try {
      const { imported } = await api.importProfileBullets();
      setMessage(`Imported ${imported} bullets from your profile.`);
      load();
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function importJson(replace) {
    setMessage(null);
    try {
      const parsed = JSON.parse(importText);
      const list = Array.isArray(parsed) ? parsed : parsed.entries;
      const { imported } = await api.importEntries(list, replace);
      setImportText("");
      setMessage(`Imported ${imported} entries.`);
      load();
    } catch (err) {
      setMessage(err instanceof SyntaxError ? "That isn't valid JSON." : err.message);
    }
  }

  async function remove(id) {
    try {
      await api.deleteEntry(id);
      load();
    } catch (err) {
      setMessage(err.message);
    }
  }

  const roleName = (key) => roles.find((r) => r.key === key)?.company ?? key;

  return (
    <>
      <form className="card form-card" onSubmit={onSubmit}>
        <h2>Log some work</h2>
        <div className="grid-2">
          <Field label="Job" name="role" as="select" value={form.role} onChange={onChange} errors={errors}>
            {roles.map((r) => (
              <option key={r.key} value={r.key}>
                {r.title}, {r.company}
              </option>
            ))}
          </Field>
          <Field label="Date" name="entry_date" type="date" value={form.entry_date} onChange={onChange} errors={errors} />
        </div>
        <Field
          label="What did you do?"
          name="raw_text"
          as="textarea"
          rows="4"
          required
          placeholder="Tools you used, the problem, and the result. Plain words are fine."
          value={form.raw_text}
          onChange={onChange}
          errors={errors}
        />
        <label className="check">
          <input type="checkbox" name="use_ai" checked={form.use_ai} onChange={onChange} /> Let the AI pull out the facts
          (counts as one run)
        </label>
        {message && <p className="hint" role="status">{message}</p>}
        <div className="form-actions">
          <button type="button" className="btn" onClick={importBullets}>
            Import profile bullets
          </button>
          <span className="spacer" />
          <button type="submit" className="btn btn-primary" disabled={busy || !roles.length}>
            {busy ? "Saving…" : "Save entry"}
          </button>
        </div>
      </form>

      <details className="card form-card">
        <summary>Import entries from the Claude version</summary>
        <Field
          label="Paste a JSON list of entries"
          name="import"
          as="textarea"
          rows="5"
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
        />
        <div className="form-actions">
          <span className="spacer" />
          <button type="button" className="btn" disabled={!importText.trim()} onClick={() => importJson(false)}>
            Add to my log
          </button>
          <button type="button" className="btn btn-danger" disabled={!importText.trim()} onClick={() => importJson(true)}>
            Replace my log
          </button>
        </div>
      </details>

      <div className="card form-card">
        <h2>Your entries {entries && <span className="muted">({entries.length})</span>}</h2>
        {entries === null ? (
          <p className="muted">Loading…</p>
        ) : entries.length === 0 ? (
          <p className="muted">Nothing yet. Import your profile bullets to start.</p>
        ) : (
          <ul className="entry-list">
            {entries.map((e) => (
              <li key={e.id}>
                <div>
                  <span className="muted">
                    #{e.id} · {e.entry_date} · {roleName(e.role)}
                    {e.source === "resume" ? " · from profile" : ""}
                  </span>
                  <p>{e.raw_text}</p>
                </div>
                <ConfirmButton question="Delete this entry?" onConfirm={() => remove(e.id)} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

// The fixed facts: contact details, titles and dates, skills, depth notes and limits.
function ProfileTab({ onSaved }) {
  const [text, setText] = useState(null);
  const [savedAt, setSavedAt] = useState(null);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .agentProfile()
      .then((p) => {
        setText(p.yaml);
        setSavedAt(p.updated_at);
      })
      .catch((err) => setMessage(err.message));
  }, []);

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setMessage(null);
    try {
      const p = await api.saveAgentProfile(text);
      setSavedAt(p.updated_at);
      setMessage("Saved.");
      onSaved(p.roles);
    } catch (err) {
      setErrors(err.fields);
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (text === null) return <p className="page-message">{message ?? "Loading…"}</p>;

  return (
    <form className="card form-card" onSubmit={save}>
      <h2>Profile</h2>
      <p className="muted">
        {savedAt
          ? `Last saved ${new Date(savedAt).toLocaleString()}.`
          : "This is a starter template. Replace the example details with your own and save."}{" "}
        Titles, dates, certifications and education are copied onto every resume exactly as written. The limits are
        rules the accuracy check enforces.
      </p>
      <Field
        label="Profile (YAML)"
        name="yaml"
        as="textarea"
        rows="24"
        spellCheck="false"
        className="code"
        value={text}
        onChange={(e) => setText(e.target.value)}
        errors={errors}
      />
      {message && <p className={errors.yaml ? "form-error" : "hint"}>{message}</p>}
      <div className="form-actions">
        <span className="spacer" />
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Saving…" : "Save profile"}
        </button>
      </div>
    </form>
  );
}

// The resume agent: turns your career log into honest, tailored resumes.
export default function ResumeAgentPage() {
  const [params, setParams] = useSearchParams();
  const tab = TABS.some((t) => t.key === params.get("tab")) ? params.get("tab") : "tailor";
  const [status, setStatus] = useState(null);
  const [roles, setRoles] = useState([]);
  const [error, setError] = useState(null);

  const loadStatus = useCallback(() => api.agentStatus().then(setStatus).catch((err) => setError(err.message)), []);
  useEffect(() => {
    loadStatus();
    api
      .agentProfile()
      .then((p) => setRoles(p.roles))
      .catch(() => {});
  }, [loadStatus]);

  const choose = (key) => {
    const next = new URLSearchParams(params);
    next.set("tab", key);
    setParams(next, { replace: true });
  };

  return (
    <div className="form-page agent-page">
      <div className="page-header">
        <div>
          <h1>Resume agent</h1>
          <p className="page-subtitle muted">
            Every resume claim is checked against your career log. Anything the log doesn't back up is removed.
          </p>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}
      {status && !status.configured && (
        <div className="notice">The agent isn't set up yet: ANTHROPIC_API_KEY is missing on the server.</div>
      )}
      {status && (
        <p className="muted agent-usage">
          {status.runs_today} of {status.daily_run_limit} AI runs used today · {status.entry_count} log entries
          {!status.has_profile && " · start on the Profile tab"}
        </p>
      )}

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={`tab ${tab === t.key ? "active" : ""}`}
            onClick={() => choose(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "tailor" && <TailorTab roles={roles} onUsage={loadStatus} />}
      {tab === "log" && <LogTab roles={roles} onUsage={loadStatus} />}
      {tab === "profile" && (
        <ProfileTab
          onSaved={(r) => {
            setRoles(r);
            loadStatus();
          }}
        />
      )}
    </div>
  );
}
