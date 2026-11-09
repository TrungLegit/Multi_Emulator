/**
 * Interactive ADR Learning Portal Viewer (public/js/adrViewer.js)
 * Deliverable for Chương — Frontend Engineer & Interactive Dashboard Lead
 * Fetches and renders Architecture Decision Records (ADR-001 to ADR-004) in Markdown.
 */

export class AdrViewer {
  constructor(listContainerId, readerContainerId) {
    this.listEl = document.getElementById(listContainerId);
    this.readerEl = document.getElementById(readerContainerId);
    this.adrs = [];
    this.activeId = null;
  }

  async loadAdrs() {
    try {
      const res = await fetch("/api/adrs");
      const data = await res.json();
      this.adrs = data.adrs || [];
      this.renderList();
      if (this.adrs.length > 0) {
        this.selectAdr(this.adrs[0].id);
      }
    } catch (err) {
      if (this.readerEl) {
        this.readerEl.innerHTML = `<p>Không thể tải danh sách ADR: ${err.message}</p>`;
      }
    }
  }

  renderList() {
    if (!this.listEl) return;
    if (!this.adrs.length) {
      this.listEl.innerHTML = `<p style="color:#94a3b8;font-size:0.8rem;">Chưa có tài liệu ADR.</p>`;
      return;
    }

    this.listEl.innerHTML = this.adrs
      .map(
        (item) => `
      <button class="adr-item-btn ${item.id === this.activeId ? "active" : ""}" data-adr-id="${item.id}">
        <div style="font-size:0.72rem;color:#38bdf8;font-weight:700;">${item.id} • ${item.status}</div>
        <div style="font-size:0.84rem;font-weight:600;margin-top:0.2rem;">${this.escapeHtml(item.title.replace(/^ADR-\d+:\s*/i, ""))}</div>
        <div style="font-size:0.7rem;color:#94a3b8;margin-top:0.2rem;">Tác giả: ${this.escapeHtml(item.author)}</div>
      </button>
    `
      )
      .join("");

    this.listEl.querySelectorAll(".adr-item-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.selectAdr(btn.getAttribute("data-adr-id"));
      });
    });
  }

  selectAdr(adrId) {
    this.activeId = adrId;
    this.renderList();
    const found = this.adrs.find((a) => a.id === adrId);
    if (!found || !this.readerEl) return;
    this.readerEl.innerHTML = this.renderMarkdown(found.content);
  }

  escapeHtml(str = "") {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  renderMarkdown(md = "") {
    const lines = md.split(/\r?\n/);
    let html = "";
    let inList = false;

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) {
        if (inList) {
          html += "</ul>";
          inList = false;
        }
        continue;
      }

      if (line.startsWith("# ")) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<h1>${this.formatInline(line.slice(2))}</h1>`;
      } else if (line.startsWith("## ")) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<h2>${this.formatInline(line.slice(3))}</h2>`;
      } else if (line.startsWith("### ")) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<h3>${this.formatInline(line.slice(4))}</h3>`;
      } else if (line.startsWith("- ") || line.match(/^\d+\.\s+/)) {
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        const itemText = line.replace(/^(-|\d+\.)\s+/, "");
        html += `<li>${this.formatInline(itemText)}</li>`;
      } else {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<p style="margin-bottom:0.65rem;">${this.formatInline(line)}</p>`;
      }
    }

    if (inList) html += "</ul>";
    return html;
  }

  formatInline(text) {
    return this.escapeHtml(text)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
  }
}
