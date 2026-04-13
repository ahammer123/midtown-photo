(function () {
  const app = document.getElementById("app");
  const bubble = document.getElementById("bubble");
  const bubbleImg = document.getElementById("bubbleImg");

  /** @type {HTMLTableRowElement | null} */
  let anchoredRow = null;
  let repositionScheduled = false;

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderTable(items) {
    const rows = items
      .map((it) => {
        const qty =
          it.quantity != null && it.quantity !== ""
            ? escapeHtml(String(it.quantity))
            : "";
        const preview = String(it.image || it.bh_preview_url || "").trim();
        const previewAttr = preview ? ` data-preview="${escapeHtml(preview)}"` : "";
        return `<tr${previewAttr} data-item="${escapeHtml(it.item)}">
          <td class="num">${qty}</td>
          <td class="item-cell"><span class="item-label">${escapeHtml(it.item)}</span></td>
          <td class="price">${escapeHtml(it.price || "")}</td>
        </tr>`;
      })
      .join("");
    return `<table class="equipment-table">
      <thead><tr>
        <th class="num">Qty</th>
        <th>Item</th>
        <th>Day rate</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  function render(data) {
    const m = data.meta || {};
    const metaLine =
      document.getElementById("brandLine") || document.getElementById("sourceLine");
    const srcText = String(m.brand_line || m.source || "").trim();
    if (metaLine) {
      if (srcText) {
        metaLine.textContent = srcText;
        metaLine.hidden = false;
      } else {
        metaLine.textContent = "";
        metaLine.hidden = true;
      }
    }
    const noticeEl = document.getElementById("noticeLine");
    if (noticeEl) {
      const noticeText = String(m.notice || "").trim();
      if (noticeText) {
        noticeEl.textContent = noticeText;
        noticeEl.hidden = false;
      } else {
        noticeEl.textContent = "";
        noticeEl.hidden = true;
      }
    }
    const pageTitle = document.getElementById("pageTitle");
    if (pageTitle) pageTitle.textContent = m.title || "Equipment list";
    const rateCaption = document.getElementById("rateCaption");
    if (rateCaption) rateCaption.textContent = m.rate_caption || "";
    const attribution = document.getElementById("attribution");
    if (attribution) attribution.textContent = m.image_attribution || "";

    const parts = [];
    for (const g of data.groups || []) {
      parts.push(`<h2 class="section-title">${escapeHtml(g.section)}</h2>`);
      for (const sub of g.subsections || []) {
        if (sub.title) {
          parts.push(`<h3 class="sub-title">${escapeHtml(sub.title)}</h3>`);
        }
        parts.push(renderTable(sub.items || []));
      }
    }
    app.innerHTML = parts.join("");
  }

  /**
   * Pin the bubble next to the row so list text stays readable (static vs cursor).
   */
  function anchorBubbleToRow(tr) {
    if (!tr || bubble.hidden) return;

    const pad = 12;
    const gap = 14;
    const rect = tr.getBoundingClientRect();

    const place = () => {
      const bw = bubble.offsetWidth || 240;
      const bh = bubble.offsetHeight || 220;

      let left = rect.right + gap;
      let top = rect.top + rect.height / 2 - bh / 2;
      let placement = "right";

      if (left + bw > window.innerWidth - pad) {
        left = rect.left - gap - bw;
        placement = "left";
      }

      if (left < pad) {
        placement = "below";
        left = rect.left + rect.width / 2 - bw / 2;
        top = rect.bottom + gap;
      }

      left = Math.max(pad, Math.min(left, window.innerWidth - bw - pad));
      top = Math.max(pad, Math.min(top, window.innerHeight - bh - pad));

      bubble.dataset.placement = placement;
      bubble.style.left = `${Math.round(left)}px`;
      bubble.style.top = `${Math.round(top)}px`;
    };

    requestAnimationFrame(() => {
      requestAnimationFrame(place);
    });
  }

  function scheduleReanchor() {
    if (!anchoredRow || repositionScheduled) return;
    repositionScheduled = true;
    requestAnimationFrame(() => {
      repositionScheduled = false;
      if (anchoredRow && bubble.classList.contains("is-visible")) {
        anchorBubbleToRow(anchoredRow);
      }
    });
  }

  function wireBubble() {
    app.addEventListener(
      "mouseover",
      (e) => {
        const tr = e.target.closest("tr[data-preview]");
        if (!tr || !tr.dataset.preview) return;
        if (tr === anchoredRow && bubble.classList.contains("is-visible")) return;

        anchoredRow = tr;
        const url = tr.dataset.preview;
        bubbleImg.alt = tr.dataset.item ? `Preview: ${tr.dataset.item}` : "Equipment preview";

        const show = () => {
          bubble.hidden = false;
          bubble.setAttribute("aria-hidden", "false");
          anchorBubbleToRow(tr);
          requestAnimationFrame(() => bubble.classList.add("is-visible"));
        };

        bubbleImg.onload = () => {
          anchorBubbleToRow(tr);
          bubbleImg.onload = null;
        };

        bubble.classList.remove("is-visible");
        bubbleImg.src = url;
        show();
      },
      true
    );

    app.addEventListener(
      "mouseout",
      (e) => {
        const tr = e.target.closest("tr[data-preview]");
        if (!tr) return;
        const related = e.relatedTarget;
        if (related && tr.contains(related)) return;
        if (related && related.nodeType === 1) {
          const nextTr = related.closest("tr[data-preview]");
          if (nextTr && nextTr !== tr) return;
        }
        anchoredRow = null;
        bubble.classList.remove("is-visible");
        bubble.hidden = true;
        bubble.setAttribute("aria-hidden", "true");
        bubbleImg.removeAttribute("src");
      },
      true
    );

    window.addEventListener("scroll", scheduleReanchor, true);
    window.addEventListener("resize", scheduleReanchor);
  }

  fetch("data.json")
    .then((r) => {
      if (!r.ok) throw new Error("Missing data.json — run: python3 build_from_pdf.py");
      return r.json();
    })
    .then((data) => {
      render(data);
      wireBubble();
    })
    .catch((err) => {
      app.innerHTML = `<p class="caption" style="color:#f88">${escapeHtml(err.message)}</p>`;
    });
})();
