import { useEffect } from "react";
import { Icon } from "../icons.jsx";
import { CATEGORY_LABEL, STATE_LABEL, STATUS_LABEL } from "../format.js";

export function Modal({ title, subtitle, onClose, children, wide = false }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "modal-wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <header className="modal-head">
          <div>
            <h2>{title}</h2>
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}

export function StatusBadge({ loan, today }) {
  if (loan.overdue) return <span className="badge badge-danger">Overdue {loan.days_overdue}d</span>;
  if (loan.status === "checked_out" && loan.due_date === today) return <span className="badge badge-warn">Due today</span>;
  if (loan.status === "returned" && loan.returned_late) return <span className="badge badge-warn">Returned late</span>;
  return <span className={`badge badge-${loan.status}`}>{STATUS_LABEL[loan.status]}</span>;
}

export function AvailabilityBadge({ asset }) {
  if (asset.state !== "in_service") return <span className={`badge badge-${asset.state}`}>{STATE_LABEL[asset.state]}</span>;
  if (asset.current_loan_id) return <span className="badge badge-checked_out">On loan</span>;
  if (!asset.available_now) return <span className="badge badge-reserved">Reserved today</span>;
  return <span className="badge badge-ok">Available</span>;
}

export function CategoryChip({ category }) {
  return (
    <span className={`cat cat-${category}`}>
      <Icon name={category} size={16} />
      {CATEGORY_LABEL[category]}
    </span>
  );
}

export function Empty({ icon = "gear", title, children }) {
  return (
    <div className="empty">
      <Icon name={icon} size={30} />
      <strong>{title}</strong>
      {children && <p className="muted">{children}</p>}
    </div>
  );
}

export function Toasts({ toasts, dismiss }) {
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`} onClick={() => dismiss(t.id)}>
          <Icon name={t.kind === "error" ? "alert" : "check"} size={18} />
          <span>{t.text}</span>
        </div>
      ))}
    </div>
  );
}

export function Field({ label, hint, error, children }) {
  return (
    <label className={`field ${error ? "field-error" : ""}`}>
      <span className="field-label">{label}</span>
      {children}
      {(error || hint) && <span className="field-hint">{error || hint}</span>}
    </label>
  );
}
