// A labelled form input that shows the API's error message for that field, if any.
export default function Field({ label, name, errors = {}, as = "input", children, hint, ...props }) {
  const Tag = as;
  const id = `field-${name}`;
  // The API sends errors as a list of messages; join them into one line.
  const error = errors[name]?.join?.(" ") ?? errors[name];

  return (
    <div className={`field ${error ? "has-error" : ""}`}>
      <label htmlFor={id}>{label}</label>
      <Tag id={id} name={name} aria-invalid={Boolean(error)} {...props}>
        {children}
      </Tag>
      {hint && !error && <small className="hint">{hint}</small>}
      {error && <small className="error">{error}</small>}
    </div>
  );
}
