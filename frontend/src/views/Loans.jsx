import { useMemo, useState } from "react";
import { Icon } from "../icons.jsx";
import { fmtRange, initials } from "../format.js";
import { CategoryChip, Empty, StatusBadge } from "../components/ui.jsx";

const TABS = [
  { key: "active", label: "Active" },
  { key: "overdue", label: "Overdue" },
  { key: "history", label: "History" },
  { key: "all", label: "All" },
];

function Actions({ loan, onAction }) {
  const act = (action) => () => onAction({ type: "transition", loan, action });
  return (
    <div className="loan-actions">
      {loan.status === "reserved" && (
        <>
          <button className="btn btn-sm btn-primary" onClick={act("checkout")}>
            <Icon name="arrowOut" size={16} /> Check out
          </button>
          <button className="icon-btn" aria-label="Edit dates" onClick={() => onAction({ type: "editLoan", loan })}>
            <Icon name="edit" size={18} />
          </button>
          <button className="btn btn-sm btn-ghost" onClick={act("cancel")}>
            Cancel
          </button>
        </>
      )}
      {loan.status === "checked_out" && (
        <button className="btn btn-sm" onClick={act("return")}>
          <Icon name="arrowIn" size={16} /> Return
        </button>
      )}
      {["reserved", "cancelled"].includes(loan.status) && (
        <button className="icon-btn icon-btn-danger" aria-label="Delete loan" onClick={() => onAction({ type: "deleteLoan", loan })}>
          <Icon name="trash" size={18} />
        </button>
      )}
    </div>
  );
}

export default function Loans({ loans, today, onAction }) {
  const [tab, setTab] = useState("active");
  const counts = useMemo(
    () => ({
      active: loans.filter((l) => ["reserved", "checked_out"].includes(l.status)).length,
      overdue: loans.filter((l) => l.overdue).length,
      history: loans.filter((l) => ["returned", "cancelled"].includes(l.status)).length,
      all: loans.length,
    }),
    [loans],
  );
  const shown = loans.filter((l) => {
    if (tab === "active") return ["reserved", "checked_out"].includes(l.status);
    if (tab === "overdue") return l.overdue;
    if (tab === "history") return ["returned", "cancelled"].includes(l.status);
    return true;
  });

  return (
    <div className="view">
      <header className="view-head">
        <div>
          <p className="eyebrow">{counts.active} active</p>
          <h1>Loans</h1>
        </div>
        <button className="btn btn-primary" onClick={() => onAction({ type: "newLoan" })}>
          <Icon name="plus" size={18} /> New reservation
        </button>
      </header>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} className={`tab ${tab === t.key ? "tab-on" : ""}`} onClick={() => setTab(t.key)}>
            {t.label} <span className="tab-n">{counts[t.key]}</span>
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <Empty icon="loans" title="No loans here" />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Gear</th>
                <th>Student</th>
                <th>Dates</th>
                <th>Status</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {shown.map((l) => (
                <tr key={l.id} className={l.overdue ? "tr-overdue" : ""}>
                  <td data-label="Loan" className="mono">#{l.id}</td>
                  <td data-label="Gear">
                    <div className="cell">
                      <strong>{l.asset_tag}</strong> <span className="muted">{l.asset_name}</span>
                      <div><CategoryChip category={l.asset_category} /></div>
                    </div>
                  </td>
                  <td data-label="Student">
                    <div className="who">
                      <span className="avatar avatar-sm">{initials(l.borrower_name)}</span>
                      <div>
                        <strong>{l.borrower_name}</strong>
                        <div className="muted mono">{l.borrower_roll}</div>
                      </div>
                    </div>
                  </td>
                  <td data-label="Dates">
                    <div className="cell">
                      {fmtRange(l.start_date, l.due_date)}
                      {l.purpose && <div className="muted">{l.purpose}</div>}
                    </div>
                  </td>
                  <td data-label="Status">
                    <div className="cell">
                      <StatusBadge loan={l} today={today} />
                    </div>
                  </td>
                  <td data-label="">
                    <Actions loan={l} onAction={onAction} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
