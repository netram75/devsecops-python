import { useMemo, useState } from "react";
import { Icon } from "../icons.jsx";
import { CATEGORY_LABEL, fmtDay } from "../format.js";
import { AvailabilityBadge, CategoryChip, Empty } from "../components/ui.jsx";

export default function Catalogue({ assets, info, onAction }) {
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [onlyFree, setOnlyFree] = useState(false);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return assets.filter(
      (a) =>
        (!category || a.category === category) &&
        (!onlyFree || a.available_now) &&
        (!q || `${a.tag} ${a.name} ${a.location}`.toLowerCase().includes(q)),
    );
  }, [assets, category, query, onlyFree]);

  return (
    <div className="view">
      <header className="view-head">
        <div>
          <p className="eyebrow">{assets.length} items</p>
          <h1>Gear catalogue</h1>
        </div>
        <button className="btn btn-primary" onClick={() => onAction({ type: "newAsset" })}>
          <Icon name="plus" size={18} /> Add gear
        </button>
      </header>

      <div className="toolbar">
        <div className="search">
          <Icon name="search" size={18} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search tag, name or location" aria-label="Search gear" />
        </div>
        <div className="chips" role="group" aria-label="Filter by category">
          <button className={`chip ${!category ? "chip-on" : ""}`} onClick={() => setCategory("")}>
            All
          </button>
          {info.categories.map((c) => (
            <button key={c} className={`chip ${category === c ? "chip-on" : ""}`} onClick={() => setCategory(category === c ? "" : c)}>
              <Icon name={c} size={15} /> {CATEGORY_LABEL[c]}
            </button>
          ))}
        </div>
        <label className="toggle">
          <input type="checkbox" checked={onlyFree} onChange={(e) => setOnlyFree(e.target.checked)} />
          <span>Available now</span>
        </label>
      </div>

      {shown.length === 0 ? (
        <Empty icon="search" title="No gear matches">Try another category or clear the search.</Empty>
      ) : (
        <div className="asset-grid">
          {shown.map((a) => (
            <article key={a.id} className={`asset ${a.state !== "in_service" ? "asset-off" : ""}`}>
              <div className="asset-top">
                <span className={`asset-icon cat-${a.category}`}>
                  <Icon name={a.category} size={26} />
                </span>
                <AvailabilityBadge asset={a} />
              </div>
              <span className="asset-tag">{a.tag}</span>
              <h3>{a.name}</h3>
              <div className="asset-meta">
                <CategoryChip category={a.category} />
                <span className="muted">· max {info.rules.max_loan_days[a.category]}d</span>
              </div>
              <p className="muted asset-loc">{a.location || "No location set"}</p>
              {a.next_reservation && <p className="asset-next">Next booking {fmtDay(a.next_reservation)}</p>}
              <footer className="asset-actions">
                <button className="btn btn-sm btn-primary" disabled={a.state !== "in_service"} onClick={() => onAction({ type: "newLoan", assetId: a.id })}>
                  Reserve
                </button>
                <button className="icon-btn" aria-label={`Edit ${a.tag}`} onClick={() => onAction({ type: "editAsset", asset: a })}>
                  <Icon name="edit" size={18} />
                </button>
                <button className="icon-btn icon-btn-danger" aria-label={`Delete ${a.tag}`} onClick={() => onAction({ type: "deleteAsset", asset: a })}>
                  <Icon name="trash" size={18} />
                </button>
              </footer>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
