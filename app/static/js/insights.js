/* Anonymous, cookie-free analytics for the owner dashboard (Owner Dashboard → Analytics).
   Sends small batches of events to /api/e. Nothing here can break the page: every step is wrapped, and events that
   fail to send are kept and retried. The owner's visits are skipped automatically while logged in; any other device
   can be excluded by opening the site once with ?notrack=1 (?track=1 turns it back on). */
(function () {
  try {
    var END = "/api/e";
    if (navigator.webdriver) return;
    var ls = window.localStorage, now = Date.now;
    var q = new URLSearchParams(location.search);
    if (q.has("notrack")) { ls.setItem("dbi_nt", "1"); note("Your visits on this device won't be counted."); }
    if (q.has("track")) { ls.removeItem("dbi_nt"); note("Counting visits on this device again."); }
    if (ls.getItem("dbi_nt") === "1") return;

    var rid = function () { return Math.random().toString(36).slice(2, 10) + now().toString(36).slice(-6); };
    var isNew = !ls.getItem("dbi_vid");
    var vid = ls.getItem("dbi_vid") || rid();
    ls.setItem("dbi_vid", vid);
    var s = {};
    try { s = JSON.parse(ls.getItem("dbi_s") || "{}"); } catch (e) {}
    if (!s.id || now() - (s.t || 0) > 30 * 60 * 1000) {
      // a new visit: remember where it came from
      var ref = document.referrer && document.referrer.indexOf(location.host) === -1 ? document.referrer : "";
      var utm = ["utm_source", "utm_medium", "utm_campaign"].map(function (k) { return q.get(k) || ""; }).join("|").replace(/\|+$/, "");
      s = { id: rid(), ref: ref, utm: utm, land: location.pathname, n: isNew };
    }
    var save = function () { s.t = now(); ls.setItem("dbi_s", JSON.stringify(s)); };
    save();

    var path = location.pathname.replace(/index\.html$/, "") || "/";
    var ctx = { vid: vid, sid: s.id, tz: (Intl.DateTimeFormat().resolvedOptions().timeZone || ""), lang: navigator.language,
      ref: s.ref, utm: s.utm, new: s.n, p: path };
    var queue = [];
    try { queue = JSON.parse(ls.getItem("dbi_q") || "[]").slice(-200); } catch (e) {}
    ls.removeItem("dbi_q");

    var track = function (k, l, v) { queue.push({ k: k, p: path, l: l == null ? undefined : String(l).slice(0, 200), v: v, t: now() }); save(); };
    window.dbTrack = function (k, l, v) { try { track(k, l, v); } catch (e) {} };

    var body = function (list) {
      var t = now();
      return JSON.stringify({ c: ctx, e: list.map(function (e) { return { k: e.k, p: e.p, l: e.l, v: e.v, a: (t - e.t) / 1000 }; }) });
    };
    var sending = false;
    function flush(leaving) {
      flushTime();
      if (!queue.length) return;
      var batch = queue.splice(0, 60);
      if (leaving) {
        // page is closing: hand the batch to the browser, and keep a copy in case it never arrives
        var ok = navigator.sendBeacon && navigator.sendBeacon(END, new Blob([body(batch)], { type: "text/plain" }));
        if (!ok) queue = batch.concat(queue);
        if (queue.length) ls.setItem("dbi_q", JSON.stringify(queue));
        return;
      }
      if (sending) { queue = batch.concat(queue); return; }
      sending = true;
      fetch(END, { method: "POST", body: body(batch), headers: { "Content-Type": "text/plain" }, keepalive: true, credentials: "same-origin" })
        .then(function (r) { if (!r.ok && r.status !== 204) throw 0; })
        .catch(function () { queue = batch.concat(queue); ls.setItem("dbi_q", JSON.stringify(queue.slice(-200))); })
        .then(function () { sending = false; });
    }

    // ---- time actually spent: counts only while the tab is visible and someone moved, scrolled or typed in the last minute
    var active = 0, lastInput = now(), lastTick = now(), sentAt = 0;
    ["pointermove", "pointerdown", "keydown", "scroll", "touchstart", "wheel"].forEach(function (ev) { addEventListener(ev, function () { lastInput = now(); }, { passive: true }); });
    setInterval(function () {
      var t = now();
      if (document.visibilityState === "visible" && t - lastInput < 60000) active += (t - lastTick) / 1000;
      lastTick = t;
    }, 1000);
    function flushTime() { var d = Math.round(active - sentAt); if (d >= 1) { queue.push({ k: "time", p: path, v: d, t: now() }); sentAt += d; } }

    // ---- scroll depth
    var maxDepth = 0, sentDepth = 0;
    function depth() {
      var h = document.documentElement.scrollHeight - innerHeight;
      maxDepth = Math.max(maxDepth, h > 0 ? Math.min(100, Math.round((100 * scrollY) / h)) : 100);
    }
    addEventListener("scroll", depth, { passive: true });

    // ---- Call / Text / Email taps, social and other outbound links, button clicks
    document.addEventListener("click", function (e) {
      var el = e.target.closest && e.target.closest("a, button");
      if (!el) return;
      var label = (el.getAttribute("data-track") || el.getAttribute("aria-label") || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60);
      var href = el.getAttribute("href") || "";
      if (/^tel:/i.test(href)) return track("call", href.replace(/^tel:/i, ""));
      if (/^sms:/i.test(href)) return track("text", href.replace(/^sms:/i, ""));
      if (/^mailto:/i.test(href)) return track("email");
      if (/^https?:/i.test(href) && el.host && el.host !== location.host) return track("outbound", el.host.replace(/^(www|m|l)\./, ""));
      if (label && !el.closest("form")) track("click", label);
    }, true);

    // ---- gallery videos (the play event doesn't bubble, so listen in the capture phase)
    var played = {};
    document.addEventListener("play", function (e) {
      var src = (e.target.currentSrc || e.target.src || "").split("/").pop();
      if (e.target.tagName === "VIDEO" && src && !played[src]) { played[src] = 1; track("video", src); }
    }, true);

    // ---- estimate form: first touch = started; server-side errors on reload = which fields; confirmation page = sent
    var started = {};
    document.addEventListener("focusin", function (e) {
      var f = e.target.closest && e.target.closest("form");
      if (f && !started[f.id || "form"]) { started[f.id || "form"] = 1; track("form_start", f.id || "form"); flush(); }
    });

    // ---- send: right away for the page view, then every 10s, and when the page is hidden/closed
    track("view", document.title.slice(0, 120));
    if (/\/request-estimate\/confirmation/.test(path)) track("form_submit");
    var bad = [].slice.call(document.querySelectorAll(".field-errors")).map(function (ul) {
      var f = ul.parentNode && ul.parentNode.querySelector("input, textarea, select");
      return f && f.name;
    }).filter(Boolean);
    if (bad.length) track("form_error", bad.join(","));
    flush();
    setInterval(function () { if (maxDepth > sentDepth) { track("scroll", null, maxDepth); sentDepth = maxDepth; } flush(); }, 10000);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") { if (maxDepth > sentDepth) { track("scroll", null, maxDepth); sentDepth = maxDepth; } flush(true); }
    });
    addEventListener("pagehide", function () { flush(true); });
    depth();
  } catch (e) {}

  function note(msg) {
    try {
      var d = document.createElement("div");
      d.textContent = msg;
      d.style.cssText = "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:99999;background:#fff;color:#07080d;font:700 14px system-ui,sans-serif;padding:12px 18px;border-radius:99px;box-shadow:0 10px 30px rgba(0,0,0,.3)";
      (document.body || document.documentElement).appendChild(d);
      setTimeout(function () { d.remove(); }, 3500);
    } catch (e) {}
  }
})();
