/**
 * Multi_Emulator — Main Frontend Application Controller (public/js/app.js)
 * Deliverable for Chương — Frontend Engineer & Interactive Dashboard Lead
 *
 * Implements:
 * - Phone Farm Matrix View (7x3 Grid like reference image)
 * - Synchronized Touch/Tap/Swipe across all linked screens
 * - App Switcher (TikTok, Facebook, Instagram, YouTube, AFK Game)
 * - Ultra-Lite Resource Optimization & Instance Config Modal
 * - Live Terminal Log Viewer & Toast Notifications
 */

import { RealtimeClient } from "./websocket.js";
import { AdrViewer } from "./adrViewer.js";

const APP_THEMES = {
  tiktok: {
    label: "TikTok",
    iconHtml: "♪",
    iconClass: "tiktok-icon",
    pkg: "com.ss.android.ugc.trill",
    subtitle: "@ForYou • Trending",
  },
  facebook: {
    label: "Facebook",
    iconHtml: "f",
    iconClass: "facebook-icon",
    pkg: "com.facebook.katana",
    subtitle: "News Feed • Lite",
  },
  instagram: {
    label: "Instagram",
    iconHtml: "◎",
    iconClass: "instagram-icon",
    pkg: "com.instagram.android",
    subtitle: "Reels & Stories",
  },
  youtube: {
    label: "YouTube",
    iconHtml: "▶",
    iconClass: "youtube-icon",
    pkg: "com.google.android.youtube",
    subtitle: "Shorts Auto-Play",
  },
  idle_game: {
    label: "Treo Game",
    iconHtml: "⚔",
    iconClass: "game-icon",
    pkg: "com.lilithgame.hgame.gp",
    subtitle: "AFK Auto-Farming",
  },
};

class MultiEmulatorApp {
  constructor() {
    this.state = {
      summary: {
        discoveredCount: 0,
        connectedCount: 0,
        syncedCount: 0,
        activeSyncGroups: 0,
      },
      instances: [],
      selectedIds: new Set(),
      currentAppFilter: "all",
      activeGlobalApp: "tiktok",
      syncEnabled: true,
      autoScrollTimer: null,
      logFilter: "ALL",
      browserProfiles: [],
    };

    this.adrViewer = new AdrViewer("adr-list-container", "adr-reader-container");
    this.realtime = new RealtimeClient({
      onEvent: (evt) => this.handleRealtimeEvent(evt),
      onStatusChange: (ok, text) => this.updateWsBadge(ok, text),
    });
  }

  async init() {
    this.bindNavigation();
    this.bindSliders();
    this.bindModal();
    this.realtime.connect();

    // Load initial state; if fewer than 6 instances exist, auto-load the 21-slot Phone Farm Box preset
    await this.loadInitialFarm();
    this.bindBrowserHub();
    await this.loadBrowserProfiles();
    await this.adrViewer.loadAdrs();
  }

  async loadInitialFarm() {
    try {
      const res = await fetch("/api/instances?preset=farm21");
      const data = await res.json();
      this.applyState(data);
      this.appendLog(
        `Đã khởi tạo Phone Farm Box (${data.instances?.length || 0} máy ảo siêu nhẹ sẵn sàng).`
      );
    } catch (err) {
      this.appendLog(`Lỗi tải dữ liệu ban đầu: ${err.message}`, "ERROR");
    }
  }

  applyState(data) {
    if (!data) return;
    if (data.summary) {
      this.state.summary = data.summary;
    }
    if (Array.isArray(data.instances)) {
      this.state.instances = data.instances;
      if (this.state.selectedIds.size === 0) {
        data.instances.forEach((inst) => this.state.selectedIds.add(inst.id));
      }
    }
    this.renderMetrics();
    this.renderSidebarDeviceChecklist();
    this.renderPhoneMatrix();
    this.renderInstancesTable();
  }

  /* ------------------------------------------------------------------------
     1. Render Overview Metric Cards
     ------------------------------------------------------------------------ */
  renderMetrics() {
    const instances = this.state.instances || [];
    const running = instances.filter((i) => i.status === "RUNNING");
    const synced = instances.filter((i) => i.connectionState === "SYNCED");
    const totalRamMb = running.reduce(
      (acc, i) => acc + (i.metrics?.ramUsageMb || 0),
      0
    );
    const avgCpu =
      running.length > 0
        ? (
            running.reduce((acc, i) => acc + (i.metrics?.cpuPercent || 0), 0) /
            running.length
          ).toFixed(1)
        : "0.0";

    this.setText("stat-discovered", instances.length);
    this.setText("stat-connected", running.length);
    this.setText("stat-synced", synced.length);
    this.setText("stat-groups", this.state.summary.activeSyncGroups ?? 1);
    this.setText("stat-ram-total", `${(totalRamMb / 1024).toFixed(1)} GB`);
    this.setText("stat-cpu-avg", `${avgCpu}%`);
  }

  /* ------------------------------------------------------------------------
     2. Render Left Sidebar Device Checklist
     ------------------------------------------------------------------------ */
  renderSidebarDeviceChecklist() {
    const container = document.getElementById("sidebar-device-list");
    if (!container) return;
    const instances = this.state.instances || [];

    container.innerHTML = instances
      .map((inst, idx) => {
        const checked = this.state.selectedIds.has(inst.id) ? "checked" : "";
        const isRunning = inst.status === "RUNNING";
        return `
        <div class="sidebar-device-item">
          <label>
            <input type="checkbox" data-check-id="${inst.id}" ${checked} />
            <span>#${String(idx + 1).padStart(2, "0")} ${inst.id} (${inst.port})</span>
          </label>
          <span style="color:${isRunning ? "#16a34a" : "#64748b"};font-weight:700;">
            ${isRunning ? "ON" : "OFF"}
          </span>
        </div>
      `;
      })
      .join("");

    container.querySelectorAll("input[data-check-id]").forEach((chk) => {
      chk.addEventListener("change", (e) => {
        const id = e.target.getAttribute("data-check-id");
        if (e.target.checked) this.state.selectedIds.add(id);
        else this.state.selectedIds.delete(id);
      });
    });

    const logFilterSelect = document.getElementById("log-instance-filter");
    if (logFilterSelect && logFilterSelect.options.length <= 1) {
      instances.forEach((inst) => {
        const opt = document.createElement("option");
        opt.value = inst.id;
        opt.textContent = `${inst.id} (${inst.name})`;
        logFilterSelect.appendChild(opt);
      });
    }
  }

  /* ------------------------------------------------------------------------
     3. Render 7x3 Phone Matrix Grid (Matches Attached Reference Image)
     ------------------------------------------------------------------------ */
  renderPhoneMatrix() {
    const grid = document.getElementById("emu-grid");
    if (!grid) return;

    const instances = this.state.instances || [];
    if (!instances.length) {
      grid.innerHTML = `<div style="padding:2rem;color:#334155;font-weight:600;">Chưa có máy ảo nào. Nhấn "Scan Emulators" hoặc "Load 21-Phone Box" để bắt đầu.</div>`;
      return;
    }

    grid.innerHTML = instances
      .map((inst, index) => {
        const slotNum = String(index + 1).padStart(2, "0");
        const isRunning = inst.status === "RUNNING";
        const appKey = inst.activeApp || this.state.activeGlobalApp || "tiktok";
        const appMeta = APP_THEMES[appKey] || APP_THEMES.tiktok;
        const ramMb = inst.metrics?.ramUsageMb || 0;
        const fps = inst.metrics?.fps || 0;

        return `
        <div class="phone-bezel ${inst.isMaster ? "is-master" : ""} ${!isRunning ? "is-stopped" : ""}"
             data-instance-id="${inst.id}"
             title="${inst.name} (${inst.host}:${inst.port}) — Click màn hình để Tap đồng bộ">
          <div class="phone-top-chin">
            <span class="phone-slot-badge">${slotNum}</span>
            <div class="phone-earpiece"></div>
            <span class="phone-fps-tag">${isRunning ? `${fps}fps` : "OFF"}</span>
          </div>

          <div class="phone-screen ${!isRunning ? "stopped-screen" : ""}"
               onclick="window.app.handlePhoneScreenTap(event, '${inst.id}')">
            <div class="android-status-bar">
              <span>${inst.id}</span>
              <span>${inst.isMaster ? "👑 MASTER" : "5G • 100%"}</span>
            </div>

            ${
              isRunning
                ? `
              <div class="phone-app-stage" id="stage-${inst.id}">
                <div class="app-icon-box ${appMeta.iconClass}">
                  ${appMeta.iconHtml}
                </div>
                <div class="phone-app-caption">${appMeta.label}</div>
                <div style="font-size:0.53rem;color:#64748b;">${appMeta.subtitle}</div>
              </div>
              <div class="phone-metrics-overlay">
                <span>${ramMb}MB</span>
                <span>:${inst.port}</span>
              </div>
            `
                : `
              <div style="text-align:center;padding:1rem;">
                <div style="font-size:1.2rem;margin-bottom:0.2rem;">⏻</div>
                <div style="font-size:0.62rem;font-weight:700;">STOPPED</div>
              </div>
            `
            }
          </div>

          <div class="phone-bottom-chin">
            <button class="phone-mini-btn" onclick="window.app.toggleInstancePower('${inst.id}', '${inst.status}')" title="Bật / Tắt máy">
              ${isRunning ? "■" : "▶"}
            </button>
            <div class="phone-home-circle" onclick="window.app.sendQuickKey('KEYCODE_HOME')" title="Home"></div>
            <button class="phone-mini-btn" onclick="window.app.optimizeSingle('${inst.id}')" title="Tối ưu RAM">⚡</button>
          </div>
        </div>
      `;
      })
      .join("");
  }

  /* ------------------------------------------------------------------------
     4. Render Detailed Instance Table View
     ------------------------------------------------------------------------ */
  renderInstancesTable() {
    const tbody = document.getElementById("instances-table-body");
    if (!tbody) return;

    tbody.innerHTML = (this.state.instances || [])
      .map(
        (inst) => `
      <tr>
        <td><strong>${inst.id}</strong> ${inst.isMaster ? "👑" : ""}</td>
        <td>${inst.name}</td>
        <td><code>${inst.host}:${inst.port}</code></td>
        <td>${inst.resolution || "360x640"} (${inst.dpi || 160} DPI)</td>
        <td><span style="color:${inst.status === "RUNNING" ? "#22c55e" : "#94a3b8"};font-weight:700;">${inst.status}</span></td>
        <td>${inst.connectionState}</td>
        <td>${inst.metrics?.cpuPercent || 0}% / ${inst.metrics?.ramUsageMb || 0} MB</td>
        <td>
          <div style="display:flex;gap:0.35rem;">
            <button class="ctrl-btn primary" onclick="window.app.startOne('${inst.id}')">Start</button>
            <button class="ctrl-btn" onclick="window.app.stopOne('${inst.id}')">Stop</button>
            <button class="ctrl-btn" onclick="window.app.optimizeSingle('${inst.id}')">⚡ Lite</button>
            <button class="ctrl-btn danger" onclick="window.app.deleteOne('${inst.id}')">Xóa</button>
          </div>
        </td>
      </tr>
    `
      )
      .join("");
  }

  /* ------------------------------------------------------------------------
     5. Interactive Phone Screen Tap & Visual Synchronized Ripple
     ------------------------------------------------------------------------ */
  async handlePhoneScreenTap(event, sourceId) {
    const screenEl = event.currentTarget;
    const rect = screenEl.getBoundingClientRect();
    const relX = (event.clientX - rect.left) / rect.width;
    const relY = (event.clientY - rect.top) / rect.height;

    const androidX = Math.round(relX * 360);
    const androidY = Math.round(relY * 640);

    // Show ripple on the clicked phone or all synced phones
    const targetIds = this.state.syncEnabled
      ? this.state.instances.filter((i) => i.status === "RUNNING").map((i) => i.id)
      : [sourceId];

    this.triggerVisualRipple(targetIds, relX, relY);

    const cmd = `input tap ${androidX} ${androidY}`;
    const cmdInput = document.getElementById("sync-cmd");
    if (cmdInput) cmdInput.value = cmd;

    await this.broadcastCustomCommand(cmd, false);
  }

  triggerVisualRipple(instanceIds, relX = 0.5, relY = 0.5) {
    instanceIds.forEach((id) => {
      const card = document.querySelector(`.phone-bezel[data-instance-id="${id}"] .phone-screen`);
      if (!card) return;
      const ripple = document.createElement("div");
      ripple.className = "tap-ripple";
      ripple.style.left = `${Math.round(relX * 100)}%`;
      ripple.style.top = `${Math.round(relY * 100)}%`;
      card.appendChild(ripple);
      setTimeout(() => ripple.remove(), 580);
    });
  }

  triggerVisualSwipe(direction = "up") {
    const dy = direction === "up" ? -12 : 12;
    document.querySelectorAll(".phone-app-stage").forEach((stage) => {
      stage.style.transform = `translateY(${dy}px)`;
      setTimeout(() => {
        stage.style.transform = "translateY(0)";
      }, 230);
    });
  }

  /* ------------------------------------------------------------------------
     6. Core Actions & API Integration (Compatible with PLAN.md & Tests)
     ------------------------------------------------------------------------ */
  async scanEmulators() {
    this.appendLog("Đang quét các giả lập hiện có (ADB + TCP Ports + Mock Phone Farm)...");
    const res = await fetch("/api/connector/scan", { method: "POST" });
    const data = await res.json();
    this.applyState(data);
    this.showToast(`Đã quét thấy ${data.summary?.discoveredCount || 0} máy ảo`);
  }

  async load21PhonePreset() {
    this.appendLog("Đang nạp cấu hình 21 máy ảo Phone Farm Box (7x3 Matrix)...");
    const res = await fetch("/api/instances", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: "farm21", count: 21 }),
    });
    const data = await res.json();
    this.applyState(data);
    this.showToast("Đã kích hoạt dàn 21 máy Phone Farm Box!");
  }

  async connectAllEmulators() {
    this.appendLog("Đang kết nối tất cả máy ảo và gom vào Primary Sync Hub...");
    const res = await fetch("/api/connector/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ autoLink: true }),
    });
    const data = await res.json();
    this.applyState(data);
    this.showToast(`Đã kết nối & đồng bộ ${data.summary?.syncedCount || 0} máy ảo!`);
  }

  async disconnectAllEmulators() {
    this.appendLog("Đang ngắt kết nối toàn bộ dàn máy...");
    const res = await fetch("/api/connector/disconnect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    this.applyState(data);
    this.showToast("Đã dừng tất cả máy ảo.");
  }

  async toggleInstancePower(instanceId, currentStatus) {
    if (currentStatus === "RUNNING") {
      await this.stopOne(instanceId);
    } else {
      await this.startOne(instanceId);
    }
  }

  async startOne(instanceId) {
    const res = await fetch(`/api/instances/${instanceId}/start`, { method: "POST" });
    const data = await res.json();
    this.applyState(data);
    this.showToast(`Đã bật ${instanceId}`);
  }

  async stopOne(instanceId) {
    const res = await fetch(`/api/instances/${instanceId}/stop`, { method: "POST" });
    const data = await res.json();
    this.applyState(data);
    this.showToast(`Đã tắt ${instanceId}`);
  }

  async optimizeSingle(instanceId) {
    const res = await fetch(`/api/instances/${instanceId}/optimize`, { method: "POST" });
    const data = await res.json();
    this.applyState(data);
    this.showToast(`Đã tối ưu RAM siêu nhẹ cho ${instanceId}`);
  }

  async optimizeAllEmulators() {
    this.appendLog("Đang chạy ADB Optimizer: Tắt animation, giới hạn tiến trình nền cho cả dàn...");
    await this.broadcastCustomCommand(
      "settings put global window_animation_scale 0.0 && am kill-all",
      false
    );
    this.showToast("Đã tối ưu hóa RAM/CPU siêu nhẹ cho toàn bộ dàn máy!");
  }

  async deleteOne(instanceId) {
    const res = await fetch(`/api/instances/${instanceId}/delete`, { method: "POST" });
    const data = await res.json();
    this.applyState(data);
    this.showToast(`Đã xóa ${instanceId}`);
  }

  async switchAppOnAll(appKey) {
    this.state.activeGlobalApp = appKey;
    const appMeta = APP_THEMES[appKey] || APP_THEMES.tiktok;

    document.querySelectorAll("[data-app-btn]").forEach((btn) => {
      btn.classList.toggle("active-app", btn.getAttribute("data-app-btn") === appKey);
    });

    const cmd = `monkey -p ${appMeta.pkg} -c android.intent.category.LAUNCHER 1`;
    await this.broadcastCustomCommand(cmd, true, appKey);
    this.showToast(`Đã mở ${appMeta.label} đồng loạt trên tất cả máy!`);
  }

  async sendQuickSwipe(direction = "up") {
    this.triggerVisualSwipe(direction);
    const cmd =
      direction === "up"
        ? "input swipe 180 520 180 140 250"
        : "input swipe 180 140 180 520 250";
    await this.broadcastCustomCommand(cmd, false);
  }

  async sendQuickKey(keycode = "KEYCODE_HOME") {
    this.triggerVisualRipple(
      this.state.instances.filter((i) => i.status === "RUNNING").map((i) => i.id),
      0.5,
      0.88
    );
    await this.broadcastCustomCommand(`input keyevent ${keycode}`, false);
  }

  async broadcastCommand() {
    const input = document.getElementById("sync-cmd");
    const cmd = input ? input.value.trim() : "";
    if (!cmd) return;
    await this.broadcastCustomCommand(cmd, true);
  }

  async broadcastCustomCommand(cmd, showNotification = true, appOverride = null) {
    const res = await fetch("/api/connector/broadcast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cmd, app: appOverride }),
    });
    const data = await res.json();
    if (data.error) {
      this.appendLog(`Lỗi Broadcast: ${data.error}`, "ERROR");
      return;
    }
    this.applyState(data);
    const count = data.broadcast?.targetCount || 0;
    this.appendLog(`Broadcast [${count} máy] -> ${cmd}`);
    if (showNotification) {
      this.showToast(`Đã gửi lệnh đồng bộ tới ${count} máy ảo`);
    }
  }

  toggleAutoReelScroll() {
    const btn = document.getElementById("btn-auto-scroll");
    if (this.state.autoScrollTimer) {
      clearInterval(this.state.autoScrollTimer);
      this.state.autoScrollTimer = null;
      if (btn) btn.textContent = "🔄 Auto Lướt Video: OFF";
      this.showToast("Đã tắt chế độ tự động lướt TikTok/Reels");
      return;
    }

    const delaySec = Number(document.getElementById("slider-delay")?.value || 4);
    if (btn) btn.textContent = `🔄 Auto Lướt: ON (${delaySec}s)`;
    this.showToast(`Bắt đầu tự động lướt video mỗi ${delaySec} giây`);
    this.sendQuickSwipe("up");
    this.state.autoScrollTimer = setInterval(() => {
      this.sendQuickSwipe("up");
    }, delaySec * 1000);
  }

  /* ------------------------------------------------------------------------
     7. UI Helpers: Tabs, Sliders, Modals, Logs & Toasts
     ------------------------------------------------------------------------ */
  bindNavigation() {
    document.querySelectorAll(".nav-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        const target = tab.getAttribute("data-tab");
        document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
        tab.classList.add("active");
        document.getElementById(`panel-${target}`)?.classList.add("active");
      });
    });
  }

  bindSliders() {
    const bindSlider = (sliderId, labelId, suffix = "", onChange = null) => {
      const s = document.getElementById(sliderId);
      const l = document.getElementById(labelId);
      if (!s || !l) return;
      s.addEventListener("input", () => {
        l.textContent = `${s.value}${suffix}`;
        if (onChange) onChange(s.value);
      });
    };

    bindSlider("slider-speed", "val-speed", " ms");
    bindSlider("slider-delay", "val-delay", " s");
    bindSlider("slider-fps", "val-fps", " FPS");
    bindSlider("slider-scale", "val-scale", "px", (val) => {
      const grid = document.getElementById("emu-grid");
      if (grid) {
        grid.style.gridTemplateColumns = `repeat(auto-fill, minmax(${val}px, 1fr))`;
      }
    });
  }

  bindModal() {
    const modal = document.getElementById("create-modal");
    const openBtn = document.getElementById("btn-open-create-modal");
    const closeBtn = document.getElementById("btn-close-create-modal");
    const form = document.getElementById("create-instance-form");

    if (openBtn && modal) {
      openBtn.addEventListener("click", () => modal.classList.add("open"));
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener("click", () => modal.classList.remove("open"));
    }
    if (form && modal) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
          name: document.getElementById("new-inst-name").value.trim() || "Phone-Custom",
          profile: document.getElementById("new-inst-profile").value,
          resolution: document.getElementById("new-inst-res").value,
          dpi: Number(document.getElementById("new-inst-dpi").value),
          ramMb: Number(document.getElementById("new-inst-ram").value),
          activeApp: document.getElementById("new-inst-app").value,
        };
        const res = await fetch("/api/instances", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        this.applyState(data);
        modal.classList.remove("open");
        this.showToast(`Đã tạo máy ảo mới: ${payload.name}`);
      });
    }
  }

  handleRealtimeEvent(evt) {
    if (!evt || !evt.event) return;
    const msg = evt.payload?.message || JSON.stringify(evt.payload || {});
    this.appendLog(`[${evt.event}] ${msg}`);
    if (evt.event.startsWith("BROWSER_PROFILE_")) this.loadBrowserProfiles();
  }

  bindBrowserHub() {
    const bind = (id, handler) => document.getElementById(id)?.addEventListener("click", handler);
    bind("browser-refresh", () => this.loadBrowserProfiles());
    bind("browser-create", () => this.createBrowserProfiles());
    bind("browser-start-all", () => this.runBrowserProfileAction("start"));
    bind("browser-stop-all", () => this.runBrowserProfileAction("stop"));
    bind("browser-click-selector", () => {
      const selector = document.getElementById("browser-selector")?.value.trim();
      if (selector) this.syncBrowserAction(`click ${selector}`);
      else this.showToast("Nhập CSS selector trước");
    });
    bind("browser-type-submit", () => {
      const text = document.getElementById("browser-type-text")?.value;
      if (text) this.syncBrowserAction(`type ${text}`);
      else this.showToast("Nhập nội dung cần gõ trước");
    });
    document.querySelector("[data-browser-nav]")?.addEventListener("click", () => this.navigateBrowserProfiles());
    document.querySelectorAll("[data-browser-command]").forEach((button) => button.addEventListener("click", () => this.syncBrowserAction(button.dataset.browserCommand)));
    document.querySelectorAll("[data-browser-quick-url]").forEach((button) => button.addEventListener("click", () => {
      const input = document.getElementById("browser-url");
      if (input) input.value = button.dataset.browserQuickUrl;
      this.navigateBrowserProfiles(button.dataset.browserQuickUrl);
    }));
    document.getElementById("browser-profile-grid")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-profile-action]");
      if (!button) return;
      this.runBrowserProfileAction(button.dataset.profileAction, button.dataset.profileId);
    });
  }

  async browserApi(path, body) {
    const response = await fetch(path, body ? {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    } : undefined);
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  }

  async loadBrowserProfiles() {
    const summary = document.getElementById("browser-profile-summary");
    try {
      const data = await this.browserApi("/api/browser/profiles");
      this.state.browserProfiles = data.profiles || [];
      this.renderBrowserProfiles();
    } catch (err) {
      if (summary) summary.textContent = `Không tải được profiles: ${err.message}`;
    }
  }

  renderBrowserProfiles() {
    const profiles = this.state.browserProfiles;
    const running = profiles.filter((profile) => profile.isAlive).length;
    const summary = document.getElementById("browser-profile-summary");
    const grid = document.getElementById("browser-profile-grid");
    if (summary) summary.textContent = `${profiles.length} profiles · ${running} đang chạy · ${profiles.length - running} đã dừng`;
    if (!grid) return;
    if (!profiles.length) {
      grid.innerHTML = '<div class="browser-empty">Chưa có profile. Tạo profile mới để bắt đầu.</div>';
      return;
    }
    grid.innerHTML = profiles.map((profile) => {
      const isRunning = Boolean(profile.isAlive);
      const browser = (profile.browser_type || "browser").toUpperCase();
      return `<article class="browser-profile-card ${isRunning ? "is-running" : ""}">
        <div class="browser-profile-card-head"><span class="browser-icon">🌐</span><span class="browser-status ${isRunning ? "online" : "offline"}">${isRunning ? "ĐANG CHẠY" : "ĐÃ DỪNG"}</span></div>
        <h3>${this.escapeHtml(profile.name || profile.id)}</h3><p>${this.escapeHtml(profile.id)} · ${this.escapeHtml(browser)}</p>
        <p>Cổng CDP: <code>${this.escapeHtml(profile.debug_port)}</code></p>
        <div class="browser-profile-actions"><button class="ctrl-btn primary" data-profile-action="start" data-profile-id="${this.escapeHtml(profile.id)}">▶ Chạy</button><button class="ctrl-btn danger" data-profile-action="stop" data-profile-id="${this.escapeHtml(profile.id)}">■ Dừng</button></div>
      </article>`;
    }).join("");
  }

  escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  }

  async createBrowserProfiles() {
    const count = Number(document.getElementById("browser-create-count")?.value || 1);
    const browserType = document.getElementById("browser-create-type")?.value || "auto";
    if (!Number.isInteger(count) || count < 1 || count > 50) return this.showToast("Số lượng profile phải từ 1 đến 50");
    try {
      const data = await this.browserApi("/api/browser/profiles/create", { count, browserType });
      this.appendLog(`Đã tạo ${data.createdCount ?? data.profiles?.length ?? count} browser profile.`);
      this.showToast("Đã tạo browser profiles");
      await this.loadBrowserProfiles();
    } catch (err) { this.appendLog(`Lỗi tạo profile: ${err.message}`, "ERROR"); }
  }

  async runBrowserProfileAction(action, profileId = null) {
    try {
      const data = await this.browserApi(`/api/browser/profiles/${action}`, profileId ? { profileId } : {});
      this.appendLog(`Browser ${action}: ${JSON.stringify(data.results || data.result || data.stoppedIds || data).slice(0, 500)}`);
      await this.loadBrowserProfiles();
    } catch (err) { this.appendLog(`Lỗi browser ${action}: ${err.message}`, "ERROR"); }
  }

  async navigateBrowserProfiles(url = null) {
    const target = url || document.getElementById("browser-url")?.value.trim();
    if (!target) return this.showToast("Nhập URL cần mở");
    await this.syncBrowserAction(`goto ${target}`);
  }

  async syncBrowserAction(command) {
    try {
      const data = await this.browserApi("/api/browser/sync", { command });
      const broadcast = data.broadcast || {};
      const outcomes = broadcast.results || [];
      const succeeded = outcomes.filter((result) => result.ok).length;
      this.appendLog(`Browser sync “${command}”: ${succeeded}/${broadcast.targetCount ?? outcomes.length} thành công.`);
      if (outcomes.length) outcomes.forEach((result) => this.appendLog(`[${result.instanceId || result.name}] ${result.ok ? "OK" : "ERROR"}: ${result.output || result.error || ""}`));
      this.showToast(`Đã gửi thao tác tới ${broadcast.targetCount ?? outcomes.length} profile`);
    } catch (err) { this.appendLog(`Lỗi browser sync: ${err.message}`, "ERROR"); }
  }

  updateWsBadge(isOnline, text) {
    const label = document.getElementById("ws-status-text");
    if (label) label.textContent = text;
  }

  appendLog(msg, level = "INFO") {
    const box = document.getElementById("log-box");
    if (!box) return;
    const ts = new Date().toLocaleTimeString();
    box.textContent = `[${ts}] [${level}] ${msg}\n` + box.textContent;
  }

  showToast(message) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const item = document.createElement("div");
    item.className = "toast-item";
    item.textContent = message;
    container.appendChild(item);
    setTimeout(() => item.remove(), 3200);
  }

  setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = String(val);
  }
}

// Initialize app and expose legacy global helpers so existing scripts/tests work seamlessly
const app = new MultiEmulatorApp();
window.app = app;
window.scanEmulators = () => app.scanEmulators();
window.connectAllEmulators = () => app.connectAllEmulators();
window.disconnectAllEmulators = () => app.disconnectAllEmulators();
window.broadcastCommand = () => app.broadcastCommand();

window.addEventListener("DOMContentLoaded", () => {
  app.init();
});
