// Draws the owner Analytics dashboard from the stats endpoint and refreshes every 30 seconds.
const $ = (id) => document.getElementById(id);
const C = { pink: "#f2c14e", coral: "#e07a3f", violet: "#b9832f", cyan: "#7fd1b9", ok: "#3ddc97", mute: "#8f96aa", line: "rgba(255,255,255,.07)" };
const PALETTE = [C.pink, C.violet, C.cyan, C.coral, "#f5e6c4", "#8a6a2f", "#9aa1b4", "#c7b08a"];
let range = "7d", charts = {};
try { range = localStorage.getItem("ins_range") || "7d"; } catch (e) {}

Chart.defaults.color = C.mute;
Chart.defaults.font.family = "Inter, system-ui, sans-serif";
Chart.defaults.font.weight = 700;
Chart.defaults.plugins.legend.display = false;
Chart.defaults.plugins.tooltip.backgroundColor = "#fff";
Chart.defaults.plugins.tooltip.titleColor = "#07080d";
Chart.defaults.plugins.tooltip.bodyColor = "#07080d";
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 10;
Chart.defaults.animation.duration = 700;

const fmtN = (n) => (n >= 10000 ? (n / 1000).toFixed(1) + "k" : Math.round(n).toLocaleString());
const fmtT = (s) => (s < 60 ? Math.round(s) + "s" : Math.floor(s / 60) + "m " + String(Math.round(s % 60)).padStart(2, "0") + "s");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const ago = (iso) => { const s = (Date.now() - new Date(iso)) / 1000; return s < 60 ? "just now" : s < 3600 ? Math.floor(s / 60) + "m ago" : s < 86400 ? Math.floor(s / 3600) + "h ago" : Math.floor(s / 86400) + "d ago"; };
const grad = (ctx, a, b) => { const g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.clientHeight || 300); g.addColorStop(0, a); g.addColorStop(1, b); return g; };

function chart(id, cfg) {
  if (charts[id]) { charts[id].data = cfg.data; charts[id].update(); return charts[id]; }
  return (charts[id] = new Chart($(id), cfg));
}

const KPIS = [
  ["visitors", "Visitors", fmtN], ["pageviews", "Page views", fmtN], ["avg_time", "Avg. time per visit", fmtT],
  ["bounce", "Bounce rate", (v) => v + "%", true], ["requests", "Estimate requests", fmtN, false, true], ["calls", "Call & text taps", fmtN, false, true],
];

function renderKpis(d) {
  const box = $("kpis");
  if (!box.children.length) box.innerHTML = KPIS.map(([k, label, , , hot]) => `<div class="kpi${hot ? " hot" : ""}"><small>${label}</small><b id="k_${k}">–</b><span class="d" id="d_${k}"></span><div class="pad"></div><canvas id="s_${k}"></canvas></div>`).join("");
  const s = d.series;
  const spark = { visitors: s.visitors, pageviews: s.pageviews, requests: s.conversions, calls: s.conversions, avg_time: s.visitors, bounce: s.pageviews };
  KPIS.forEach(([k, , f, inverse]) => {
    $("k_" + k).textContent = f(d.kpis[k] || 0);
    const dl = d.deltas[k], el = $("d_" + k);
    if (dl == null) { el.textContent = d.range === "all" ? "all time" : "new"; el.className = "d"; }
    else { const good = inverse ? dl < 0 : dl > 0; el.textContent = (dl > 0 ? "▲ " : dl < 0 ? "▼ " : "") + Math.abs(dl) + "%"; el.className = "d " + (dl === 0 ? "" : good ? "up" : "down"); }
    chart("s_" + k, { type: "line", data: { labels: s.labels, datasets: [{ data: spark[k], borderColor: C.pink, borderWidth: 2, pointRadius: 0, tension: 0.4, fill: true,
      backgroundColor: (c) => grad(c.chart.ctx, "rgba(242,193,78,.28)", "rgba(242,193,78,0)") }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false, beginAtZero: true } } } });
  });
}

function niceLabel(l, hourly) {
  const [date, time] = l.split(" ");
  const dt = new Date(date + "T" + (time || "00:00") + ":00");
  return hourly ? dt.toLocaleTimeString([], { hour: "numeric" }) : dt.toLocaleDateString([], { month: "short", day: "numeric" });
}

function renderTraffic(s) {
  chart("cTraffic", { data: { labels: s.labels.map((l) => niceLabel(l, s.hourly)), datasets: [
    { type: "line", label: "Visitors", data: s.visitors, borderColor: C.pink, borderWidth: 3, pointRadius: 0, pointHoverRadius: 5, tension: 0.4, fill: true,
      backgroundColor: (c) => grad(c.chart.ctx, "rgba(242,193,78,.35)", "rgba(242,193,78,0)"), order: 1 },
    { type: "bar", label: "Page views", data: s.pageviews, backgroundColor: "rgba(185,131,47,.45)", borderRadius: 6, order: 2, maxBarThickness: 26 },
    { type: "line", label: "Calls & requests", data: s.conversions, borderColor: C.cyan, borderWidth: 0, pointRadius: (c) => (c.raw ? 5 : 0), pointBackgroundColor: C.cyan, showLine: false, order: 0 },
  ] }, options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
    scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 10, maxRotation: 0 } }, y: { beginAtZero: true, grid: { color: C.line }, ticks: { precision: 0 } } } } });
}

function renderFunnel(f) {
  const top = f[0].n || 1;
  $("funnel").innerHTML = f.map((s, i) => {
    const pct = Math.round((100 * s.n) / top), prev = i ? f[i - 1].n : null;
    const drop = i && prev ? `<div class="fdrop">${prev ? Math.round((100 * s.n) / prev) : 0}% of the step before</div>` : "";
    return `<div class="fstep"><div class="row"><span>${s.step}</span><b>${fmtN(s.n)} · ${pct}%</b></div><div class="fbar"><i style="width:${Math.max(pct, s.n ? 2 : 0)}%"></i></div>${drop}</div>`;
  }).join("");
}

const ICON = { view: "👀", call: "📞", text: "💬", email: "✉️", video: "▶️", form_start: "✍️", form_error: "⚠️", form_submit: "🎉", click: "👆", outbound: "↗️" };
function feedText(e) {
  const where = e.path === "/" ? "the homepage" : e.path;
  return ({ view: `Viewed ${where}`, call: `Tapped Call${e.label ? " · " + e.label : ""}`, text: "Tapped Text", email: "Tapped Email", video: "Played a gallery video",
    form_start: "Started the estimate form", form_error: `Form missing: ${e.label || "fields"}`, form_submit: "Sent an estimate request 🎉",
    click: `Clicked “${e.label}”`, outbound: `Opened ${e.label}` })[e.kind] || e.kind;
}
function renderFeed(feed) {
  $("feedN").textContent = feed.length ? "latest " + feed.length : "";
  $("feed").innerHTML = feed.length ? feed.map((e) => `<li><span class="ic${["form_submit", "call", "text"].includes(e.kind) ? " win" : ""}">${ICON[e.kind] || "•"}</span>
    <div class="what">${esc(feedText(e))}<span>${esc(e.region || "Unknown")} · ${esc(e.device || "")} ${esc(e.os || "")} · ${esc(e.src || "")}</span></div><time>${ago(e.ts)}</time></li>`).join("")
    : `<li class="empty">No activity yet. It shows up here the moment someone visits.</li>`;
}

const barList = (items, key = "pct", fmt = (v) => v + "%", max = 100) => items.length
  ? items.map((x) => `<div class="bar"><div class="row">${esc(x.label)}<span>${fmt(x[key])}</span></div><div class="t"><i style="width:${max ? (100 * x[key]) / max : 0}%"></i></div></div>`).join("")
  : `<div class="empty">No data yet.</div>`;

function renderDist(id, items, color) {
  chart(id, { type: "bar", data: { labels: items.map((x) => x.label), datasets: [{ data: items.map((x) => x.n), backgroundColor: color, borderRadius: 8, maxBarThickness: 46 }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: C.line }, ticks: { precision: 0 } } } } });
}

function donut(id, legId, items) {
  const total = items.reduce((a, b) => a + b.n, 0) || 1;
  chart(id, { type: "doughnut", data: { labels: items.map((x) => x.label), datasets: [{ data: items.length ? items.map((x) => x.n) : [1], backgroundColor: items.length ? PALETTE : ["rgba(255,255,255,.08)"], borderWidth: 0, hoverOffset: 6 }] },
    options: { responsive: false, cutout: "68%", plugins: { tooltip: { enabled: !!items.length } } } });
  $(legId).innerHTML = items.length ? items.map((x, i) => `<div><i style="background:${PALETTE[i % PALETTE.length]}"></i>${esc(x.label)}<span>${Math.round((100 * x.n) / total)}%</span></div>`).join("") : `<div class="empty">No data yet.</div>`;
}

function table(id, head, rows) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  $(id).innerHTML = `<div class="tr hd"><span>${head[0]}</span><span class="n">${head[1]}</span><span class="n">${head[2]}</span></div>` +
    (rows.length ? rows.map((r) => `<div class="tr"><span class="nm"><i style="width:calc(${(100 * r[1]) / max}% + 8px)"></i>${esc(r[0])}</span><span class="n">${fmtN(r[1])}</span><span class="n">${r[2]}</span></div>`).join("")
      : `<div class="empty">No data yet.</div>`);
}

const tags = (items) => items.length ? `<div class="tags">${items.map((x) => `<span>${esc(x.label)}<b>${x.n}</b></span>`).join("")}</div>` : `<div class="empty">None yet.</div>`;
const mini = (label, v) => `<div class="mini"><small>${label}</small><b>${v}</b></div>`;

function renderHeat(h) {
  const max = Math.max(1, ...h.flat()), days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  let html = `<span></span>` + Array.from({ length: 24 }, (_, i) => `<span class="hr">${i % 3 === 0 ? (i % 12 || 12) + (i < 12 ? "a" : "p") : ""}</span>`).join("");
  h.forEach((row, d) => {
    html += `<span class="lb">${days[d]}</span>` + row.map((v, hr) => {
      const a = v / max;
      return `<span class="c" data-t="${days[d]} ${(hr % 12 || 12)}${hr < 12 ? "am" : "pm"} · ${v} views" style="${v ? `background:rgba(242,193,78,${0.15 + a * 0.85});box-shadow:0 0 ${a * 14}px rgba(242,193,78,${a * 0.6})` : ""}"></span>`;
    }).join("");
  });
  $("heat").innerHTML = html;
}

async function load() {
  try {
    const r = await fetch(`${window.STATS_URL}?range=${range}`, { cache: "no-store", credentials: "same-origin" });
    if (r.redirected || r.status === 401) { location.reload(); return; }
    const d = await r.json();
    $("liveN").textContent = d.live;
    renderKpis(d);
    renderTraffic(d.series);
    renderFunnel(d.funnel);
    $("calledN").textContent = d.called ? `+ ${d.called} visits tapped Call / Text` : "";
    renderFeed(d.feed);
    $("reach").innerHTML = barList(d.reach);
    renderDist("cTime", d.time_dist, "rgba(242,193,78,.75)");
    renderDist("cDepth", d.depth, "rgba(127,209,185,.65)");
    const f = d.form;
    $("form").innerHTML = `<div class="minis">${mini("Opened", f.opened)}${mini("Sent", f.sent)}${mini("Errors", f.errors)}${mini("Open → send", f.rate + "%")}</div>
      <div class="sub">Fields people missed</div>${tags(f.fields)}`;
    const c = d.contact;
    $("contact").innerHTML = `<div class="minis">${mini("Call taps", c.calls)}${mini("Text taps", c.texts)}${mini("Email taps", c.emails)}${mini("Social clicks", c.social.reduce((a, b) => a + b.n, 0))}</div>
      <div class="sub">Social</div>${tags(c.social)}`;
    $("clicks").innerHTML = `<div class="sub" style="margin-top:0">Gallery videos played</div>${tags(d.videos)}<div class="sub">Top clicks</div>${tags(d.clicks)}`;
    table("sources", ["Source", "Visits", "Took action"], d.sources.map((x) => [x.label, x.n, x.conv ? `<span class="pill">${x.conv}</span>` : "–"]));
    table("pages", ["Page", "Views", "Avg time"], d.pages.map((p) => [p.path, p.views, fmtT(p.avg)]));
    donut("cDevice", "devLeg", d.devices);
    donut("cNew", "newLeg", [{ label: "New", n: d.newret.new }, { label: "Returning", n: d.newret.returning }].filter((x) => x.n));
    $("tech").innerHTML = `<div class="sub" style="margin-top:0">Browsers</div>${tags(d.browsers)}<div class="sub">Systems</div>${tags(d.os)}<div class="sub">Languages</div>${tags(d.langs)}`;
    const gmax = Math.max(1, ...d.regions.map((x) => x.n));
    $("geo").innerHTML = `<div class="sub" style="margin-top:0">Countries</div>${tags(d.countries)}<div class="sub">Regions</div><div class="bars">${barList(d.regions, "n", (v) => v, gmax)}</div>`;
    renderHeat(d.heat);
    $("upd").textContent = "Updated " + new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch (e) {
    $("upd").textContent = "Couldn't refresh, retrying…";
  }
}

document.querySelectorAll("#seg button").forEach((b) => {
  b.classList.toggle("on", b.dataset.r === range);
  b.addEventListener("click", () => {
    range = b.dataset.r;
    try { localStorage.setItem("ins_range", range); } catch (e) {}
    document.querySelectorAll("#seg button").forEach((x) => x.classList.toggle("on", x === b));
    load();
  });
});
load();
setInterval(load, 30000);
