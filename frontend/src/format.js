// Formats numbers as whole US dollars, e.g. $120,000.
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

// Turns a salary range into text like "$100,000 – $120,000", or null if none was given.
export function formatSalary(min, max) {
  if (min == null && max == null) return null;
  if (min != null && max != null) return `${money.format(min)} – ${money.format(max)}`;
  return min != null ? `From ${money.format(min)}` : `Up to ${money.format(max)}`;
}

// Turns "2026-03-14" into "Mar 14, 2026".
export function formatDate(iso) {
  if (!iso) return null;
  // Dates from the API are plain "YYYY-MM-DD"; read them as local dates so they don't shift a day.
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/** "today", "yesterday", "5 days ago", "3 weeks ago"… for a timestamp from the API. */
export function timeAgo(iso, now = new Date()) {
  if (!iso) return null;
  const days = Math.floor((now - new Date(iso)) / 864e5);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  if (days < 60) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}
