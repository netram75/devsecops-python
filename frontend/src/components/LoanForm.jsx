import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { CATEGORY_LABEL, addDays, diffDays, fmtDay } from "../format.js";
import { Field, Modal } from "./ui.jsx";

const STRIP_DAYS = 14;

// Days an active loan blocks the asset: [start, due), and a checked-out item stays
// blocked until it is actually returned, even when overdue. Mirrors the backend rule.
function blockedDays(loans, today, ignoreId) {
  const blocked = new Map();
  for (const l of loans) {
    if (l.id === ignoreId || !["reserved", "checked_out"].includes(l.status)) continue;
    let end = l.due_date;
    if (l.status === "checked_out" && end <= today) end = addDays(today, 1);
    for (let d = l.start_date; d < end; d = addDays(d, 1)) blocked.set(d, l);
  }
  return blocked;
}

export default function LoanForm({ info, assets, loan, presetAssetId, onClose, onSaved }) {
  const editing = Boolean(loan);
  const today = info.today;
  const lendable = assets.filter((a) => a.state === "in_service");
  const [form, setForm] = useState({
    asset_id: loan?.asset_id ?? presetAssetId ?? lendable[0]?.id ?? "",
    borrower_name: loan?.borrower_name ?? "",
    borrower_roll: loan?.borrower_roll ?? "",
    borrower_email: loan?.borrower_email ?? "",
    purpose: loan?.purpose ?? "",
    start_date: loan?.start_date ?? today,
    due_date: loan?.due_date ?? addDays(today, 2),
  });
  const [assetLoans, setAssetLoans] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const asset = assets.find((a) => a.id === Number(form.asset_id));
  const maxDays = asset ? info.rules.max_loan_days[asset.category] : 1;
  const length = diffDays(form.start_date, form.due_date);

  useEffect(() => {
    if (!form.asset_id) return;
    let live = true;
    api.assetLoans(form.asset_id).then((l) => live && setAssetLoans(l), () => live && setAssetLoans([]));
    return () => {
      live = false;
    };
  }, [form.asset_id]);

  const blocked = useMemo(() => blockedDays(assetLoans, today, loan?.id), [assetLoans, today, loan]);
  const clash = useMemo(() => {
    for (let d = form.start_date; d < form.due_date; d = addDays(d, 1)) if (blocked.has(d)) return blocked.get(d);
    return null;
  }, [blocked, form.start_date, form.due_date]);

  const set = (k) => (e) => {
    const value = e.target.value;
    const next = { ...form, [k]: value };
    if (k === "start_date" && next.due_date <= value) next.due_date = addDays(value, 1);
    setForm(next);
  };

  function pickDay(day) {
    if (blocked.has(day)) return;
    setForm({ ...form, start_date: day, due_date: addDays(day, Math.min(2, maxDays)) });
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const saved = editing
        ? await api.updateLoan(loan.id, { start_date: form.start_date, due_date: form.due_date, purpose: form.purpose })
        : await api.createLoan({ ...form, asset_id: Number(form.asset_id) });
      onSaved(saved, editing ? `Loan #${saved.id} updated` : `Reserved ${saved.asset_tag} for ${saved.borrower_name}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  const days = Array.from({ length: STRIP_DAYS }, (_, i) => addDays(today, i));

  return (
    <Modal
      wide
      title={editing ? `Edit loan #${loan.id}` : "New reservation"}
      subtitle={`Max ${info.rules.max_active_loans} active loans per student · book up to ${info.rules.max_advance_days} days ahead`}
      onClose={onClose}
    >
      <form className="form" onSubmit={submit}>
        <Field label="Gear">
          <select value={form.asset_id} onChange={set("asset_id")} disabled={editing} required>
            {lendable.map((a) => (
              <option key={a.id} value={a.id}>
                {a.tag} · {a.name} ({CATEGORY_LABEL[a.category]})
              </option>
            ))}
          </select>
        </Field>

        {asset && (
          <div className="strip" aria-label="Availability for the next two weeks">
            <div className="strip-head">
              <span>Next {STRIP_DAYS} days for {asset.tag}</span>
              <span className="strip-legend">
                <i className="dot dot-free" /> free <i className="dot dot-busy" /> booked <i className="dot dot-pick" /> your dates
              </span>
            </div>
            <div className="strip-days">
              {days.map((d) => {
                const busyLoan = blocked.get(d);
                const picked = d >= form.start_date && d < form.due_date;
                const cls = busyLoan ? (picked ? "day-clash" : "day-busy") : picked ? "day-pick" : "day-free";
                return (
                  <button
                    type="button"
                    key={d}
                    className={`day ${cls}`}
                    onClick={() => pickDay(d)}
                    title={busyLoan ? `Loan #${busyLoan.id} · ${busyLoan.borrower_name}` : `Start on ${fmtDay(d)}`}
                  >
                    <span className="day-dow">{fmtDay(d, { weekday: "narrow" })}</span>
                    <span className="day-num">{fmtDay(d, { day: "numeric" })}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="form-row">
          <Field label="Student name">
            <input value={form.borrower_name} onChange={set("borrower_name")} required disabled={editing} placeholder="Asha Verma" />
          </Field>
          <Field label="Roll number" hint="e.g. 24BCS10329">
            <input
              value={form.borrower_roll}
              onChange={set("borrower_roll")}
              required
              disabled={editing}
              pattern="[0-9]{2}[A-Za-z]{2,4}[0-9]{3,6}"
              placeholder="24BCS10329"
            />
          </Field>
        </div>
        <div className="form-row">
          <Field label="Email">
            <input type="email" value={form.borrower_email} onChange={set("borrower_email")} required disabled={editing} placeholder="asha@campus.edu" />
          </Field>
          <Field label="Purpose">
            <input value={form.purpose} onChange={set("purpose")} maxLength={200} placeholder="Photography club shoot" />
          </Field>
        </div>
        <div className="form-row">
          <Field label="Pick up on">
            <input type="date" value={form.start_date} min={today} max={addDays(today, info.rules.max_advance_days)} onChange={set("start_date")} required />
          </Field>
          <Field
            label="Return by"
            error={length > maxDays ? `${asset ? CATEGORY_LABEL[asset.category] : "This"} loans last at most ${maxDays} days` : ""}
            hint={`${length} day${length === 1 ? "" : "s"} · max ${maxDays}`}
          >
            <input type="date" value={form.due_date} min={addDays(form.start_date, 1)} onChange={set("due_date")} required />
          </Field>
        </div>
        {clash && (
          <div className="form-warn">
            {asset.tag} is booked by loan #{clash.id} ({clash.borrower_name}) on those dates. The API will refuse this with 409.
          </div>
        )}
        {error && <div className="form-error">{error}</div>}
        <footer className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={busy || !lendable.length}>
            {busy ? "Saving…" : editing ? "Save dates" : "Reserve"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
