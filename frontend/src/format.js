export const CATEGORY_LABEL = {
  camera: "Camera",
  drone: "Drone",
  audio: "Audio",
  lab_kit: "Lab kit",
  laptop: "Laptop",
  vr: "VR headset",
};

export const STATUS_LABEL = {
  reserved: "Reserved",
  checked_out: "Checked out",
  returned: "Returned",
  cancelled: "Cancelled",
};

export const STATE_LABEL = { in_service: "In service", maintenance: "Maintenance", retired: "Retired" };

// Dates from the API are plain YYYY-MM-DD strings in campus time; keep them timezone-free.
export function parseDay(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

export function addDays(iso, n) {
  const d = parseDay(iso);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function diffDays(a, b) {
  return Math.round((parseDay(b) - parseDay(a)) / 86400000);
}

export function fmtDay(iso, opts = { day: "numeric", month: "short" }) {
  return parseDay(iso).toLocaleDateString("en-IN", { ...opts, timeZone: "UTC" });
}

export function fmtRange(start, due) {
  return `${fmtDay(start)} → ${fmtDay(due)}`;
}

export function timeAgo(isoTime) {
  const seconds = Math.max(0, (Date.now() - new Date(isoTime).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return `${Math.floor(seconds / 86400)} d ago`;
}

export function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");
}
