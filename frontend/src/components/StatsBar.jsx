export default function StatsBar({ stats }) {
  if (!stats) return null;
  const count = (status) => stats.by_status.find((s) => s.status === status)?.count ?? 0;

  const items = [
    { label: "Total applications", value: stats.total },
    { label: "Interviewing", value: count("interviewing") },
    { label: "Offers", value: count("offer") },
    {
      label: "Response rate",
      value: `${Math.round(stats.response_rate * 100)}%`,
      hint: "Share of sent applications that led to an interview or offer",
    },
  ];

  return (
    <section className="stats" aria-label="Summary">
      {items.map((item) => (
        <div className="stat" key={item.label} title={item.hint}>
          <div className="stat-value">{item.value}</div>
          <div className="stat-label">{item.label}</div>
        </div>
      ))}
    </section>
  );
}
