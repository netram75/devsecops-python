import { useState } from "react";
import { api } from "../api.js";
import { CATEGORY_LABEL, STATE_LABEL } from "../format.js";
import { Field, Modal } from "./ui.jsx";

export default function AssetForm({ asset, info, onClose, onSaved }) {
  const editing = Boolean(asset);
  const [form, setForm] = useState({
    tag: asset?.tag ?? "",
    name: asset?.name ?? "",
    category: asset?.category ?? "camera",
    location: asset?.location ?? "",
    notes: asset?.notes ?? "",
    state: asset?.state ?? "in_service",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { tag, ...rest } = form;
      const saved = editing ? await api.updateAsset(asset.id, rest) : await api.createAsset(form);
      onSaved(saved, editing ? `Updated ${saved.tag}` : `Added ${saved.tag} to the catalogue`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <Modal title={editing ? `Edit ${asset.tag}` : "Add gear"} subtitle="Items students can borrow" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <div className="form-row">
          <Field label="Asset tag" hint="e.g. CAM-014 — printed on the item">
            <input value={form.tag} onChange={set("tag")} disabled={editing} required placeholder="CAM-014" />
          </Field>
          <Field label="Category" hint={`Max loan ${info?.rules.max_loan_days[form.category] ?? "–"} days`}>
            <select value={form.category} onChange={set("category")}>
              {(info?.categories ?? Object.keys(CATEGORY_LABEL)).map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_LABEL[c]}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Name">
          <input value={form.name} onChange={set("name")} required minLength={2} placeholder="Sony A7 IV body + 28-70mm" />
        </Field>
        <div className="form-row">
          <Field label="Location">
            <input value={form.location} onChange={set("location")} placeholder="Media Lab, Block B" />
          </Field>
          <Field label="State">
            <select value={form.state} onChange={set("state")}>
              {Object.entries(STATE_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Notes">
          <textarea value={form.notes} onChange={set("notes")} rows={2} placeholder="Comes with 2 batteries and a 128 GB card" />
        </Field>
        {error && <div className="form-error">{error}</div>}
        <footer className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Saving…" : editing ? "Save changes" : "Add gear"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
