import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth.jsx";
import Field from "../components/Field.jsx";
import { Intro } from "./LoginPage.jsx";

// Sign-up page: creates an account and logs straight in.
export default function RegisterPage() {
  const { register } = useAuth();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  // Keep the form state in sync with whatever the user types.
  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  // Create the account; on failure, show the API's messages next to each field.
  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setMessage(null);
    try {
      await register(form);
    } catch (err) {
      setErrors(err.fields);
      setMessage(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <Intro />
      <section className="card auth-card">
        <h2>Create your account</h2>
        <form onSubmit={onSubmit}>
          <Field label="Name" name="full_name" autoComplete="name" value={form.full_name} onChange={onChange} errors={errors} />
          <Field
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={onChange}
            errors={errors}
          />
          <Field
            label="Password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            hint="At least 8 characters, and not a common password."
            value={form.password}
            onChange={onChange}
            errors={errors}
          />
          {/* Only show a general error if no single field was to blame. */}
          {message && Object.keys(errors).length === 0 && (
            <p className="form-error" role="alert">
              {message}
            </p>
          )}
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="muted center">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </section>
    </div>
  );
}
