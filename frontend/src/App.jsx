import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Icon, Logo } from "./icons.jsx";
import { Toasts } from "./components/ui.jsx";
import AssetForm from "./components/AssetForm.jsx";
import LoanForm from "./components/LoanForm.jsx";
import Dashboard from "./views/Dashboard.jsx";
import Catalogue from "./views/Catalogue.jsx";
import Loans from "./views/Loans.jsx";

const VIEWS = [
  { key: "dashboard", label: "Dashboard", icon: "dashboard" },
  { key: "gear", label: "Gear", icon: "gear" },
  { key: "loans", label: "Loans", icon: "loans" },
];
const POLL_MS = 15000;

const currentView = () => {
  const key = window.location.hash.replace("#/", "");
  return VIEWS.some((v) => v.key === key) ? key : "dashboard";
};

export default function App() {
  const [view, setView] = useState(currentView);
  const [data, setData] = useState({ info: null, stats: null, assets: [], loans: [], activity: [] });
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [loadError, setLoadError] = useState("");
  const [modal, setModal] = useState(null);
  const [toasts, setToasts] = useState([]);
  const toastId = useRef(0);

  const toast = useCallback((text, kind = "ok") => {
    const id = ++toastId.current;
    setToasts((t) => [...t, { id, text, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === "error" ? 7000 : 3500);
  }, []);

  const load = useCallback(async () => {
    try {
      const [info, stats, assets, loans, activity] = await Promise.all([
        api.info(),
        api.stats(),
        api.assets(),
        api.loans(),
        api.activity(12),
      ]);
      setData({ info, stats, assets, loans, activity });
      setStatus("ready");
      setLoadError("");
    } catch (err) {
      setLoadError(err.message);
      setStatus((s) => (s === "ready" ? "ready" : "error"));
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    const onHash = () => setView(currentView());
    window.addEventListener("hashchange", onHash);
    return () => {
      clearInterval(timer);
      window.removeEventListener("hashchange", onHash);
    };
  }, [load]);

  const go = (key) => {
    window.location.hash = `#/${key}`;
  };

  async function onAction(a) {
    try {
      switch (a.type) {
        case "newLoan":
          return setModal({ kind: "loan", presetAssetId: a.assetId });
        case "editLoan":
          return setModal({ kind: "loan", loan: a.loan });
        case "newAsset":
          return setModal({ kind: "asset" });
        case "editAsset":
          return setModal({ kind: "asset", asset: a.asset });
        case "transition": {
          const l = await api.transition(a.loan.id, a.action);
          const verb = { checkout: "checked out", return: "returned", cancel: "cancelled" }[a.action];
          toast(`${l.asset_tag} ${verb}${l.returned_late ? " (late)" : ""}`);
          break;
        }
        case "deleteLoan":
          if (!window.confirm(`Delete loan #${a.loan.id}?`)) return;
          await api.deleteLoan(a.loan.id);
          toast(`Loan #${a.loan.id} deleted`);
          break;
        case "deleteAsset":
          if (!window.confirm(`Delete ${a.asset.tag} from the catalogue?`)) return;
          await api.deleteAsset(a.asset.id);
          toast(`${a.asset.tag} deleted`);
          break;
        default:
          return;
      }
      await load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function onSaved(_, message) {
    setModal(null);
    toast(message);
    await load();
  }

  const { info } = data;
  const overdue = data.stats?.overdue ?? 0;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Logo />
          <div>
            <strong>GearLoop</strong>
            <span>Campus gear lending</span>
          </div>
        </div>
        <nav className="nav">
          {VIEWS.map((v) => (
            <a key={v.key} href={`#/${v.key}`} className={`nav-item ${view === v.key ? "nav-on" : ""}`}>
              <Icon name={v.icon} />
              <span>{v.label}</span>
              {v.key === "loans" && overdue > 0 && <span className="nav-count">{overdue}</span>}
            </a>
          ))}
        </nav>
        <div className="build">
          <Icon name="server" size={16} />
          <div>
            <span>build <b className="mono">{info?.version ?? "…"}</b></span>
            <span>pod <b className="mono">{info?.pod ?? "…"}</b></span>
            <span>{info?.environment ?? ""}</span>
          </div>
        </div>
      </aside>

      <main className="main">
        {loadError && status === "ready" && (
          <div className="banner">
            <Icon name="alert" size={18} /> Lost contact with the API ({loadError}). Retrying every {POLL_MS / 1000}s.
          </div>
        )}
        {status === "loading" && (
          <div className="state">
            <div className="spinner" />
            <p>Loading the lending desk…</p>
          </div>
        )}
        {status === "error" && (
          <div className="state state-error">
            <Icon name="alert" size={34} />
            <h2>Backend unavailable</h2>
            <p>{loadError}</p>
            <button className="btn btn-primary" onClick={load}>
              <Icon name="refresh" size={18} /> Try again
            </button>
          </div>
        )}
        {status === "ready" && view === "dashboard" && <Dashboard {...data} onAction={onAction} go={go} />}
        {status === "ready" && view === "gear" && <Catalogue assets={data.assets} info={info} onAction={onAction} />}
        {status === "ready" && view === "loans" && <Loans loans={data.loans} today={info.today} onAction={onAction} />}
      </main>

      {modal?.kind === "asset" && <AssetForm asset={modal.asset} info={info} onClose={() => setModal(null)} onSaved={onSaved} />}
      {modal?.kind === "loan" && info && (
        <LoanForm
          info={info}
          assets={data.assets}
          loan={modal.loan}
          presetAssetId={modal.presetAssetId}
          onClose={() => setModal(null)}
          onSaved={onSaved}
        />
      )}
      <Toasts toasts={toasts} dismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))} />
    </div>
  );
}
