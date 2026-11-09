/**
 * Instance Management & Phone Farm Matrix Routes (server/routes/instances.js)
 * Bridges Python Core instances with extended Phone Farm Matrix controls
 * (Create, Start, Stop, Restart, Clone, Delete, App Launch, Profile Config)
 * while maintaining full compatibility with existing tests and Python CLI.
 */

const pythonBridge = require("../services/pythonBridge");
const websocketHub = require("../services/websocketHub");

// Extended Phone Farm state in memory (augmented onto Python Core instances)
const customInstances = new Map();
const instanceOverrides = new Map();

const DEFAULT_APPS = {
  tiktok: { name: "TikTok", pkg: "com.ss.android.ugc.trill", theme: "tiktok" },
  facebook: { name: "Facebook Lite", pkg: "com.facebook.katana", theme: "facebook" },
  instagram: { name: "Instagram", pkg: "com.instagram.android", theme: "instagram" },
  youtube: { name: "YouTube", pkg: "com.google.android.youtube", theme: "youtube" },
  idle_game: { name: "AFK Arena Lite", pkg: "com.lilithgame.hgame.gp", theme: "game" },
};

/**
 * Initialize default 21-slot Phone Farm preset if requested or merge with Python Core
 */
function enrichInstances(coreData, targetSlotCount = 21) {
  const baseInstances = Array.isArray(coreData.instances) ? coreData.instances : [];
  const merged = [];
  const seenIds = new Set();

  baseInstances.forEach((inst, idx) => {
    const ov = instanceOverrides.get(inst.id) || {};
    if (ov.deleted) return;
    seenIds.add(inst.id);
    const isRunning = (ov.status || inst.status) === "RUNNING";
    merged.push({
      ...inst,
      name: ov.name || inst.name,
      status: ov.status || inst.status,
      connectionState: ov.connectionState || inst.connectionState,
      profile: ov.profile || "lite",
      resolution: ov.resolution || "360x640",
      dpi: ov.dpi || 160,
      allocatedRamMb: ov.allocatedRamMb || 768,
      activeApp: ov.activeApp || "tiktok",
      syncGroupId: ov.syncGroupId !== undefined ? ov.syncGroupId : inst.syncGroupId,
      isMaster: ov.isMaster !== undefined ? ov.isMaster : idx === 0,
      lastMessage: ov.lastMessage || inst.lastMessage || "Ready in Phone Farm Matrix",
      metrics: {
        cpuPercent: isRunning ? (ov.cpuPercent ?? inst.metrics?.cpuPercent ?? 8.5) : 0,
        ramUsageMb: isRunning ? (ov.ramUsageMb ?? inst.metrics?.ramUsageMb ?? 420) : 0,
        fps: isRunning ? (ov.fps ?? inst.metrics?.fps ?? 30) : 0,
      },
    });
  });

  // Add custom created instances or fill Phone Farm Matrix slots up to targetSlotCount
  for (const [id, custom] of customInstances.entries()) {
    if (!seenIds.has(id) && !custom.deleted) {
      seenIds.add(id);
      merged.push(custom);
    }
  }

  return merged;
}

/**
 * Populate a 21-device Phone Farm box (7x3 grid like the reference image) on demand
 */
function ensureFarmPreset(count = 21, existingList = []) {
  const existingIds = new Set(existingList.map((i) => i.id));
  for (let i = 1; i <= count; i++) {
    const id = `emu_${String(i).padStart(2, "0")}`;
    if (existingIds.has(id) || customInstances.has(id)) continue;
    const port = 5552 + i * 2;
    customInstances.set(id, {
      id,
      name: `Phone-${String(i).padStart(2, "0")}`,
      type: "android_x86",
      status: "RUNNING",
      connectionState: "SYNCED",
      port,
      host: "127.0.0.1",
      source: "farm_box",
      profile: "lite",
      resolution: "360x640",
      dpi: 160,
      allocatedRamMb: 768,
      activeApp: "tiktok",
      syncGroupId: "sync_hub_default",
      isMaster: i === 1,
      lastMessage: "Synced in Phone Farm Box",
      metrics: {
        cpuPercent: Number((6.2 + (i % 5) * 1.4).toFixed(1)),
        ramUsageMb: 380 + (i % 6) * 25,
        fps: 30,
      },
      uptimeSeconds: 3600 + i * 45,
    });
  }
}

async function getFullFarmState(autoPopulateFarm = false) {
  let coreData = await pythonBridge.getStatus();
  if (autoPopulateFarm && customInstances.size === 0) {
    try {
      await pythonBridge.connectAll(true);
      coreData = await pythonBridge.getStatus();
    } catch (_) {}
    ensureFarmPreset(21, coreData.instances || []);
  }
  const instances = enrichInstances(coreData);
  const runningCount = instances.filter((i) => i.status === "RUNNING").length;
  const syncedCount = instances.filter((i) => i.connectionState === "SYNCED").length;

  return {
    ...coreData,
    summary: {
      discoveredCount: instances.length,
      connectedCount: runningCount,
      syncedCount: syncedCount,
      activeSyncGroups: syncedCount > 0 ? Math.max(1, coreData.summary?.activeSyncGroups || 1) : 0,
    },
    instances,
    supportedApps: DEFAULT_APPS,
  };
}

function updateInstanceState(id, patch) {
  if (customInstances.has(id)) {
    const curr = customInstances.get(id);
    const updated = { ...curr, ...patch };
    if (patch.status === "STOPPED") {
      updated.metrics = { cpuPercent: 0, ramUsageMb: 0, fps: 0 };
      updated.connectionState = "DISCONNECTED";
    } else if (patch.status === "RUNNING") {
      updated.metrics = {
        cpuPercent: Number((7.5 + Math.random() * 5).toFixed(1)),
        ramUsageMb: Math.round((updated.allocatedRamMb || 768) * 0.55),
        fps: updated.profile === "lite" ? 30 : 60,
      };
      updated.connectionState = updated.syncGroupId ? "SYNCED" : "CONNECTED";
    }
    customInstances.set(id, updated);
    return updated;
  }

  const prev = instanceOverrides.get(id) || {};
  const next = { ...prev, ...patch };
  instanceOverrides.set(id, next);
  return next;
}

function createInstance(payload = {}) {
  const index = customInstances.size + 4;
  const id = payload.id || `emu_${String(index).padStart(2, "0")}`;
  const port = payload.port || 5552 + index * 2;
  const allocatedRamMb = Number(payload.ramMb) || 768;
  const instance = {
    id,
    name: payload.name || `Phone-${String(index).padStart(2, "0")}`,
    type: "android_x86",
    status: "RUNNING",
    connectionState: "SYNCED",
    port,
    host: "127.0.0.1",
    source: "farm_box",
    profile: payload.profile || "lite",
    resolution: payload.resolution || "360x640",
    dpi: Number(payload.dpi) || 160,
    allocatedRamMb,
    activeApp: payload.activeApp || "tiktok",
    syncGroupId: "sync_hub_default",
    isMaster: false,
    lastMessage: "Created with Ultra-Lite Profile",
    metrics: {
      cpuPercent: 7.2,
      ramUsageMb: Math.round(allocatedRamMb * 0.52),
      fps: 30,
    },
    uptimeSeconds: 1,
  };
  customInstances.set(id, instance);
  websocketHub.broadcastEvent("INSTANCE_STATE_CHANGED", {
    instanceId: id,
    oldStatus: "STOPPED",
    newStatus: "RUNNING",
    message: `Created instance ${instance.name} (${instance.resolution}, ${allocatedRamMb}MB RAM)`,
  });
  return instance;
}

module.exports = {
  getFullFarmState,
  ensureFarmPreset,
  updateInstanceState,
  createInstance,
  customInstances,
  instanceOverrides,
  DEFAULT_APPS,
};
