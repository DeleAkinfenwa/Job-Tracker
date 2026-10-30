import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth.jsx";
import Field from "../components/Field.jsx";

// The short pitch shown beside the login and sign-up forms.
export function Intro() {
  return (
    <section className="intro">
      <h1>Keep every job application in one place.</h1>
      <p>
        Job Tracker helps you follow each application from the first "I'd like to work there" to the final offer.
        Save companies, log the roles you apply for, and see at a glance how your search is going.
      </p>
      <ul className="intro-points">
        <li>Move applications through stages: wishlist, applied, interviewing, offer</li>
        <li>Note salary ranges, links and anything you want to remember</li>
        <li>See your totals and how often companies get back to you</li>
      </ul>
    </section>
  );
}

// Login page: one-click demo access, or log in with email and password.
export default function LoginPage() {
  const { login, loginAsDemo } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null); // "demo" | "login" | null

  // Runs a login action, showing which button is busy and any error.
  async function run(kind, action) {
    setBusy(kind);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err.status === 401 ? "That email and password don't match an account." : err.message);
      setBusy(null);
    }
  }

  // Keep the form state in sync with whatever the user types.
  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  return (
    <div className="auth-page">
      <Intro />
      <section className="card auth-card">
        {/* One-click demo login. */}
        <h2>Try it out</h2>
        <p className="muted">No sign-up needed. The demo account comes with sample data.</p>
        <button type="button" className="btn btn-primary btn-block" disabled={busy} onClick={() => run("demo", loginAsDemo)}>
          {busy === "demo" ? "Opening the demo…" : "Explore the demo"}
        </button>

        <div className="divider">or log in</div>

        {/* Regular email and password login. */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            run("login", () => login(form.email, form.password));
          }}
        >
          <Field label="Email" name="email" type="email" autoComplete="email" required value={form.email} onChange={onChange} />
          <Field
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={form.password}
            onChange={onChange}
          />
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="btn btn-block" disabled={busy}>
            {busy === "login" ? "Logging in…" : "Log in"}
          </button>
        </form>
        <p className="muted center">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </section>
    </div>
  );
}
