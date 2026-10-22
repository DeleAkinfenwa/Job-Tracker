import { useState } from "react";

// A delete button that asks "Are you sure?" on the page itself instead of a browser pop-up.
export default function ConfirmButton({ label = "Delete", question, onConfirm, className = "btn btn-danger" }) {
  const [asking, setAsking] = useState(false);

  if (!asking) {
    return (
      <button type="button" className={className} onClick={() => setAsking(true)}>
        {label}
      </button>
    );
  }
  return (
    <span className="confirm" role="group" aria-label="Confirm delete">
      {question}
      <button type="button" className="btn btn-danger" onClick={onConfirm} autoFocus>
        Yes, delete
      </button>
      <button type="button" className="btn btn-ghost" onClick={() => setAsking(false)}>
        Cancel
      </button>
    </span>
  );
}
