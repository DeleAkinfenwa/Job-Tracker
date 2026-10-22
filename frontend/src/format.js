const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export function formatSalary(min, max) {
  if (min == null && max == null) return null;
  if (min != null && max != null) return `${money.format(min)} – ${money.format(max)}`;
  return min != null ? `From ${money.format(min)}` : `Up to ${money.format(max)}`;
}

export function formatDate(iso) {
  if (!iso) return null;
  // Dates from the API are plain "YYYY-MM-DD"; read them as local dates so they don't shift a day.
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
