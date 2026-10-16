import { Icon } from "../icons.jsx";
import { CATEGORY_LABEL, fmtDay, fmtRange, initials, timeAgo } from "../format.js";
import { CategoryChip, Empty, StatusBadge } from "../components/ui.jsx";

function Kpi({ label, value, note, tone = "", icon }) {
  return (
    <div className={`kpi ${tone}`}>
      <div className="kpi-top">
        <span>{label}</span>
        <Icon name={icon} size={18} />
      </div>
      <strong>{value}</strong>
      <span className="kpi-note">{note}</span>
    </div>
  );
}

const ACTION_TONE = { reserved: "blue", checked_out: "teal", returned: "green", cancelled: "grey", created: "violet", updated: "grey", deleted: "red" };

export default function Dashboard({ stats, loans, activity, info, onAction, go }) {
  if (!stats) return null;
  const today = info.today;
  const active = loans.filter((l) => l.status === "checked_out");
  const dueBack = active
    .filter((l) => l.due_date <= today)
    .sort((a, b) => b.days_overdue - a.days_overdue || a.due_date.localeCompare(b.due_date));
  const pickups = loans
    .filter((l) => l.status === "reserved" && l.start_date <= today)
    .sort((a, b) => a.start_date.localeCompare(b.start_date));
  const upcoming = loans
    .filter((l) => l.status === "reserved" && l.start_date > today)
    .sort((a, b) => a.start_date.localeCompare(b.start_date))
    .slice(0, 4);
  const maxCat = Math.max(1, ...Object.values(stats.by_category));

  return (
    <div className="view">
      <header className="view-head">
        <div>
          <p className="eyebrow">
            {fmtDay(today, { weekday: "long", day: "numeric", month: "long" })}
            <span className="eyebrow-note"> · updated {new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
          </p>
          <h1>Lending desk</h1>
        </div>
        <button className="btn btn-primary" onClick={() => onAction({ type: "newLoan" })}>
          <Icon name="plus" size={18} /> New reservation
        </button>
      </header>

      <section className="kpis">
        <Kpi label="Available now" value={stats.assets_available_now} note={`of ${stats.assets_in_service} in service`} icon="gear" tone="kpi-teal" />
        <Kpi label="On loan" value={stats.on_loan_now} note={`${stats.utilisation_pct}% utilisation`} icon="arrowOut" />
        <Kpi label="Reserved" value={stats.loans_by_status.reserved} note={`${pickups.length} ready for pick-up`} icon="clock" />
        <Kpi
          label="Overdue"
          value={stats.overdue}
          note={stats.due_today ? `${stats.due_today} due back today` : "nothing due today"}
          icon="alert"
          tone={stats.overdue ? "kpi-danger" : ""}
        />
      </section>

      <div className="grid-2">
        <section className="card">
          <header className="card-head">
            <h2>Due back</h2>
            <span className="muted">{dueBack.length} item{dueBack.length === 1 ? "" : "s"}</span>
          </header>
          {dueBack.length === 0 ? (
            <Empty icon="check" title="Nothing overdue">Every checked-out item is within its loan window.</Empty>
          ) : (
            <ul className="rows">
              {dueBack.map((l) => (
                <li key={l.id} className="row">
                  <span className="avatar">{initials(l.borrower_name)}</span>
                  <div className="row-main">
                    <strong>{l.asset_tag} · {l.asset_name}</strong>
                    <span className="muted">
                      {l.borrower_name} · {l.borrower_roll} · due {fmtDay(l.due_date)}
                    </span>
                  </div>
                  <StatusBadge loan={l} today={today} />
                  <button className="btn btn-sm" onClick={() => onAction({ type: "transition", loan: l, action: "return" })}>
                    <Icon name="arrowIn" size={16} /> Return
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <header className="card-head">
            <h2>Ready for pick-up</h2>
            <span className="muted">{pickups.length} today</span>
          </header>
          {pickups.length === 0 ? (
            <Empty icon="clock" title="No pick-ups waiting">Reservations starting today will show here.</Empty>
          ) : (
            <ul className="rows">
              {pickups.map((l) => (
                <li key={l.id} className="row">
                  <span className="avatar avatar-blue">{initials(l.borrower_name)}</span>
                  <div className="row-main">
                    <strong>{l.asset_tag} · {l.asset_name}</strong>
                    <span className="muted">
                      {l.borrower_name} · {fmtRange(l.start_date, l.due_date)}
                    </span>
                  </div>
                  <button className="btn btn-sm btn-primary" onClick={() => onAction({ type: "transition", loan: l, action: "checkout" })}>
                    <Icon name="arrowOut" size={16} /> Check out
                  </button>
                </li>
              ))}
            </ul>
          )}
          {upcoming.length > 0 && (
            <>
              <h3 className="subhead">Coming up</h3>
              <ul className="rows rows-compact">
                {upcoming.map((l) => (
                  <li key={l.id} className="row">
                    <span className="date-pill">{fmtDay(l.start_date)}</span>
                    <div className="row-main">
                      <strong>{l.asset_tag}</strong>
                      <span className="muted">{l.borrower_name}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <header className="card-head">
            <h2>Catalogue by category</h2>
            <button className="link" onClick={() => go("gear")}>Open catalogue →</button>
          </header>
          <ul className="bars">
            {Object.entries(stats.by_category).map(([cat, n]) => (
              <li key={cat}>
                <CategoryChip category={cat} />
                <div className="bar">
                  <span style={{ width: `${(100 * n) / maxCat}%` }} />
                </div>
                <span className="bar-n">{n}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card">
          <header className="card-head">
            <h2>Activity</h2>
            <span className="muted">audit trail</span>
          </header>
          {activity.length === 0 ? (
            <Empty icon="loans" title="No activity yet" />
          ) : (
            <ol className="feed">
              {activity.map((e) => (
                <li key={e.id}>
                  <span className={`feed-dot tone-${ACTION_TONE[e.action] ?? "grey"}`} />
                  <div>
                    <span>{e.summary}</span>
                    <span className="muted feed-time">{timeAgo(e.at)}</span>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
      <p className="muted footnote">
        Loan limits: {Object.entries(info.rules.max_loan_days).map(([c, d]) => `${CATEGORY_LABEL[c]} ${d}d`).join(" · ")}
      </p>
    </div>
  );
}
