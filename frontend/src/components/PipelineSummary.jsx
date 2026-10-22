import { STATUSES } from "../api/endpoints.js";

// A summary of the whole job search: key numbers, then one bar split by stage.
export default function PipelineSummary({ stats, activeStatus, onSelect }) {
  if (!stats) return <section className="summary card summary-loading" aria-busy="true" />;

  const count = (status) => stats.by_status.find((s) => s.status === status)?.count ?? 0;
  const active = count("applied") + count("interviewing");

  const figures = [
    { label: "Applications", value: stats.total },
    { label: "In progress", value: active, hint: "Applied or interviewing" },
    { label: "Offers", value: count("offer") },
    {
      label: "Response rate",
      value: `${Math.round(stats.response_rate * 100)}%`,
      hint: "Share of sent applications that led to an interview or offer",
    },
  ];

  return (
    <section className="summary card" aria-label="Summary of your job search">
      <dl className="figures">
        {figures.map((f) => (
          <div key={f.label} className="figure" title={f.hint}>
            <dt>{f.label}</dt>
            <dd>{f.value}</dd>
          </div>
        ))}
      </dl>

      {stats.total > 0 && (
        <div className="pipeline">
          <div className="pipeline-bar" role="img" aria-label="Applications by stage">
            {STATUSES.filter((s) => count(s.value) > 0).map((s) => (
              <span
                key={s.value}
                className={`pipeline-segment stage-${s.value}`}
                style={{ flexGrow: count(s.value) }}
                title={`${s.label}: ${count(s.value)}`}
              />
            ))}
          </div>
          <div className="pipeline-legend" role="group" aria-label="Filter by stage">
            {STATUSES.map((s) => (
              <button
                key={s.value}
                type="button"
                className={`legend-item stage-${s.value} ${activeStatus === s.value ? "is-active" : ""}`}
                aria-pressed={activeStatus === s.value}
                onClick={() => onSelect(activeStatus === s.value ? "" : s.value)}
              >
                <span className="dot" aria-hidden="true" />
                {s.label}
                <span className="legend-count">{count(s.value)}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
