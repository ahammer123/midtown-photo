/**
 * Equipment list editor — static-friendly: edit in browser, save downloads data.json.
 */
const emptyPayload = () => ({
  meta: {
    source: "",
    notice: "",
    title: "EQUIPMENT LIST",
    rate_caption: "QTY  ITEM  DAY RATE",
    image_attribution: "",
  },
  groups: [
    {
      section: "I. SECTION TITLE",
      subsections: [
        {
          title: "Subsection",
          items: [
            {
              quantity: 1,
              item: "",
              price: "$0",
              image: "",
              bh_page_url: "",
              bh_preview_url: "",
            },
          ],
        },
      ],
    },
  ],
});

async function imageStemFromItem(itemText) {
  const t = String(itemText || "").trim();
  if (!t) return "";
  const data = new TextEncoder().encode(t);
  const hash = await crypto.subtle.digest("SHA-256", data);
  const hex = Array.from(new Uint8Array(hash), (b) =>
    b.toString(16).padStart(2, "0")
  ).join("");
  return `eq-${hex.slice(0, 14)}`;
}

async function ensureItemImage(it) {
  const item = String(it.item || "").trim();
  if (!item) {
    it.image = "";
    return;
  }
  const stem = await imageStemFromItem(item);
  it.image = `images/${stem}.jpg`;
}

function deepClone(obj) {
  return typeof structuredClone === "function"
    ? structuredClone(obj)
    : JSON.parse(JSON.stringify(obj));
}

async function normalizePayload(p) {
  const out = deepClone(p);
  if (!out.meta) out.meta = emptyPayload().meta;
  const m = out.meta;
  for (const k of ["source", "notice", "title", "rate_caption", "image_attribution"]) {
    if (m[k] == null) m[k] = "";
    m[k] = String(m[k]);
  }
  if (!Array.isArray(out.groups)) out.groups = [];
  for (const g of out.groups) {
    g.section = String(g.section || "");
    if (!Array.isArray(g.subsections)) g.subsections = [];
    for (const s of g.subsections) {
      s.title = String(s.title || "");
      if (!Array.isArray(s.items)) s.items = [];
      for (const it of s.items) {
        const q = parseInt(String(it.quantity), 10);
        it.quantity = Number.isFinite(q) ? q : 0;
        it.item = String(it.item || "");
        it.price = String(it.price || "");
        it.bh_page_url = String(it.bh_page_url || "");
        it.bh_preview_url = String(it.bh_preview_url || "");
        await ensureItemImage(it);
      }
    }
  }
  return out;
}

let state = null;

function setStatus(msg, type = "") {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = msg;
  el.className = "status-bar" + (type ? ` is-${type}` : "");
}

function itemRowTemplate(gi, si, ii, it) {
  return `
    <tr data-gi="${gi}" data-si="${si}" data-ii="${ii}">
      <td><input class="field-qty" type="number" min="0" step="1" value="${escapeAttr(
        it.quantity
      )}" aria-label="Quantity" /></td>
      <td><input class="field-item" type="text" value="${escapeAttr(
        it.item
      )}" placeholder="Item description" aria-label="Item" /></td>
      <td><input class="field-price" type="text" value="${escapeAttr(
        it.price
      )}" placeholder="$0" aria-label="Price" /></td>
      <td><button type="button" class="btn-icon row-del" title="Remove line">×</button></td>
    </tr>`;
}

function escapeAttr(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

function render() {
  const root = document.getElementById("editor-root");
  if (!state || !root) return;

  const meta = state.meta;
  let html = `
    <div class="meta-card">
      <h2>Page header</h2>
      <div class="meta-grid">
        <div class="field">
          <label for="m-title">Title</label>
          <input id="m-title" data-meta="title" type="text" value="${escapeAttr(
            meta.title
          )}" />
        </div>
        <div class="field">
          <label for="m-rate">Rate caption</label>
          <input id="m-rate" data-meta="rate_caption" type="text" value="${escapeAttr(
            meta.rate_caption
          )}" />
        </div>
        <div class="field field-full">
          <label for="m-notice">Notice (insurance / policy)</label>
          <textarea id="m-notice" data-meta="notice" rows="2">${escapeAttr(
            meta.notice
          )}</textarea>
        </div>
        <div class="field field-full">
          <label for="m-source">Source note (optional)</label>
          <input id="m-source" data-meta="source" type="text" value="${escapeAttr(
            meta.source
          )}" />
        </div>
        <div class="field field-full">
          <label for="m-attrib">Image footer note (optional)</label>
          <textarea id="m-attrib" data-meta="image_attribution" rows="2">${escapeAttr(
            meta.image_attribution
          )}</textarea>
        </div>
      </div>
    </div>`;

  state.groups.forEach((g, gi) => {
    html += `
      <div class="section-block" data-section="${gi}">
        <div class="section-head">
          <input type="text" class="section-title-inp" data-gi="${gi}" value="${escapeAttr(
            g.section
          )}" placeholder="Section title" aria-label="Section title" />
          <button type="button" class="btn btn-danger section-del">Delete section</button>
        </div>`;
    g.subsections.forEach((s, si) => {
      html += `
        <div class="sub-block" data-gi="${gi}" data-si="${si}">
          <div class="sub-head">
            <input type="text" class="sub-title-inp" data-gi="${gi}" data-si="${si}" value="${escapeAttr(
              s.title
            )}" placeholder="Subsection title" aria-label="Subsection title" />
            <button type="button" class="btn btn-ghost sub-del">Remove subsection</button>
          </div>
          <div class="items-wrap">
            <table class="items-table">
              <thead><tr><th>Qty</th><th>Item</th><th>Day rate</th><th></th></tr></thead>
              <tbody>
                ${s.items.map((it, ii) => itemRowTemplate(gi, si, ii, it)).join("")}
              </tbody>
            </table>
          </div>
          <div class="row-tools">
            <button type="button" class="btn btn-ghost add-row" data-gi="${gi}" data-si="${si}">+ Add line</button>
          </div>
        </div>`;
    });
    html += `
        <div class="row-tools">
          <button type="button" class="btn btn-ghost add-sub" data-gi="${gi}">+ Add subsection</button>
        </div>
      </div>`;
  });

  html += `
    <div class="row-tools" style="border:1px solid var(--border);border-radius:8px;padding:1rem;margin-top:1rem;">
      <button type="button" class="btn btn-primary" id="add-section">+ Add section</button>
    </div>
    <div class="deploy-note">
      <strong>NAS / web host</strong> Upload this whole folder as a static site. After editing, use <strong>Save changes</strong>
      and replace <code>data.json</code> beside <code>index.html</code>. Photos: run <code>sync_eq_photos.py</code> on your Mac,
      then copy the <code>images</code> folder to the server.
    </div>`;

  root.innerHTML = html;
  bindEditorEvents();
}

function readMetaFromDom() {
  document.querySelectorAll("[data-meta]").forEach((el) => {
    const key = el.getAttribute("data-meta");
    if (key && state.meta) state.meta[key] = el.value;
  });
}

function syncRowFromInputs(tr) {
  const gi = +tr.dataset.gi;
  const si = +tr.dataset.si;
  const ii = +tr.dataset.ii;
  const it = state.groups[gi]?.subsections[si]?.items[ii];
  if (!it) return;
  const qty = tr.querySelector(".field-qty");
  const item = tr.querySelector(".field-item");
  const price = tr.querySelector(".field-price");
  if (qty) it.quantity = parseInt(qty.value, 10) || 0;
  if (item) it.item = item.value;
  if (price) it.price = price.value;
}

function bindEditorEvents() {
  document.querySelectorAll(".section-title-inp").forEach((el) => {
    el.addEventListener("change", () => {
      const gi = +el.dataset.gi;
      if (state.groups[gi]) state.groups[gi].section = el.value;
    });
  });

  document.querySelectorAll(".sub-title-inp").forEach((el) => {
    el.addEventListener("change", () => {
      const gi = +el.dataset.gi;
      const si = +el.dataset.si;
      const s = state.groups[gi]?.subsections[si];
      if (s) s.title = el.value;
    });
  });

  document.querySelectorAll(".items-table tbody tr").forEach((tr) => {
    tr.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("change", () => syncRowFromInputs(tr));
    });
  });
}

function onMainClick(e) {
  const t = e.target;
  if (!(t instanceof HTMLElement)) return;
  if (t.id === "add-section") {
      readMetaFromDom();
      state.groups.push({
        section: "NEW SECTION",
        subsections: [
          {
            title: "Subsection",
            items: [
              {
                quantity: 1,
                item: "",
                price: "$0",
                image: "",
                bh_page_url: "",
                bh_preview_url: "",
              },
            ],
          },
        ],
      });
      render();
      setStatus("Added section.", "ok");
      return;
  }
  if (t.classList.contains("add-sub")) {
      readMetaFromDom();
      document.querySelectorAll(".items-table tbody tr").forEach(syncRowFromInputs);
      const gi = +t.dataset.gi;
      state.groups[gi].subsections.push({
        title: "Subsection",
        items: [
          {
            quantity: 1,
            item: "",
            price: "$0",
            image: "",
            bh_page_url: "",
            bh_preview_url: "",
          },
        ],
      });
      render();
      return;
  }
  if (t.classList.contains("add-row")) {
      readMetaFromDom();
      document.querySelectorAll(".items-table tbody tr").forEach(syncRowFromInputs);
      const gi = +t.dataset.gi;
      const si = +t.dataset.si;
      state.groups[gi].subsections[si].items.push({
        quantity: 1,
        item: "",
        price: "$0",
        image: "",
        bh_page_url: "",
        bh_preview_url: "",
      });
      render();
      return;
  }
  if (t.classList.contains("row-del")) {
      readMetaFromDom();
      document.querySelectorAll(".items-table tbody tr").forEach(syncRowFromInputs);
      const tr = t.closest("tr");
      const gi = +tr.dataset.gi;
      const si = +tr.dataset.si;
      const ii = +tr.dataset.ii;
      state.groups[gi].subsections[si].items.splice(ii, 1);
      render();
      return;
  }
  if (t.classList.contains("sub-del")) {
      readMetaFromDom();
      document.querySelectorAll(".items-table tbody tr").forEach(syncRowFromInputs);
      const sub = t.closest(".sub-block");
      const gi = +sub.dataset.gi;
      const si = +sub.dataset.si;
      if (state.groups[gi].subsections.length <= 1) {
        setStatus("Each section needs at least one subsection.", "warn");
        return;
      }
      state.groups[gi].subsections.splice(si, 1);
      render();
      return;
  }
  if (t.classList.contains("section-del")) {
      readMetaFromDom();
      document.querySelectorAll(".items-table tbody tr").forEach(syncRowFromInputs);
      const block = t.closest(".section-block");
      const gi = +block.dataset.section;
      if (state.groups.length <= 1) {
        setStatus("Keep at least one section.", "warn");
        return;
      }
      if (confirm("Delete this entire section and all lines under it?")) {
        state.groups.splice(gi, 1);
        render();
        setStatus("Section removed.", "ok");
      }
  }
}

function gatherStateFromDom() {
  readMetaFromDom();
  document.querySelectorAll(".items-table tbody tr").forEach(syncRowFromInputs);
  document.querySelectorAll(".section-title-inp").forEach((el) => {
    const gi = +el.dataset.gi;
    if (state.groups[gi]) state.groups[gi].section = el.value;
  });
  document.querySelectorAll(".sub-title-inp").forEach((el) => {
    const gi = +el.dataset.gi;
    const si = +el.dataset.si;
    const s = state.groups[gi]?.subsections[si];
    if (s) s.title = el.value;
  });
}

async function downloadJson() {
  if (!state) return;
  gatherStateFromDom();
  const out = await normalizePayload(state);
  const blob = new Blob([JSON.stringify(out, null, 2) + "\n"], {
    type: "application/json",
  });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "data.json";
  a.click();
  URL.revokeObjectURL(a.href);
  setStatus("Saved — replace data.json next to index.html, then refresh the list page.", "ok");
}

async function applyImagePaths() {
  if (!state) return;
  gatherStateFromDom();
  for (const g of state.groups) {
    for (const s of g.subsections) {
      for (const it of s.items) await ensureItemImage(it);
    }
  }
  render();
  setStatus("Image paths updated from item text (images/eq-….jpg). Add matching photos to your album and sync.", "ok");
}

function loadPayload(data) {
  if (!data || typeof data !== "object" || !Array.isArray(data.groups)) {
    throw new Error("Invalid JSON: expected { meta, groups }");
  }
  state = data;
  render();
  setStatus("Loaded. Edit below, then Save changes.", "ok");
}

async function loadFromServer() {
  const r = await fetch("data.json", { cache: "no-store" });
  if (!r.ok) throw new Error(r.statusText);
  loadPayload(await r.json());
}

function onFileSelected(ev) {
  const f = ev.target.files?.[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      loadPayload(JSON.parse(String(reader.result)));
    } catch (e) {
      setStatus("Invalid JSON file.", "warn");
    }
  };
  reader.readAsText(f);
  ev.target.value = "";
}

function init() {
  document.getElementById("admin-main")?.addEventListener("click", onMainClick);
  document.getElementById("btn-load-server")?.addEventListener("click", async () => {
    try {
      await loadFromServer();
    } catch {
      setStatus(
        "Could not load data.json. Serve this folder over HTTP or use Open file…",
        "warn"
      );
    }
  });
  document.getElementById("btn-download")?.addEventListener("click", () => downloadJson());
  document.getElementById("btn-images")?.addEventListener("click", () => applyImagePaths());
  document.getElementById("file-input")?.addEventListener("change", onFileSelected);
  document.getElementById("btn-new")?.addEventListener("click", () => {
    if (confirm("Start from a blank template? Unsaved changes will be lost.")) {
      state = emptyPayload();
      render();
      setStatus("New template — add sections and lines, then download.", "ok");
    }
  });

  loadFromServer().catch(() => {
    state = emptyPayload();
    render();
    setStatus(
      "Open data.json from disk, or serve this folder over HTTP (Reload loads it automatically).",
      "warn"
    );
  });
}

init();
