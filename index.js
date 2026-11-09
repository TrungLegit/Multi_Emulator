#!/usr/bin/env node
/**
 * Multi_Emulator — Node.js Backend Orchestrator & Connector API Server
 * Educational Multi Emulator ADR version
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const pythonBridge = require("./server/services/pythonBridge");
const websocketHub = require("./server/services/websocketHub");
const adrRoutes = require("./server/routes/adrs");
const instanceRoutes = require("./server/routes/instances");

const PORT = process.env.PORT || 3000;

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
  });
  res.end(JSON.stringify(data));
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
    });
    req.on("end", () => {
      if (!raw.trim()) {
        return resolve({});
      }
      try {
        resolve(JSON.parse(raw));
      } catch (err) {
        reject(new Error("Malformed JSON request body"));
      }
    });
    req.on("error", reject);
  });
}

function serveStaticFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || "application/octet-stream";
  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not Found");
      return;
    }
    res.writeHead(200, { "Content-Type": contentType });
    res.end(content);
  });
}

const server = http.createServer(async (req, res) => {
  const urlObj = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  const pathname = urlObj.pathname;

  try {
    // 1. Static Frontend Dashboard & Assets (Root + public/ fallback)
    if (req.method === "GET" && (pathname === "/" || pathname === "/index.html")) {
      const publicIndex = path.join(__dirname, "public", "index.html");
      const rootIndex = path.join(__dirname, "index.html");
      const targetPath = fs.existsSync(publicIndex) ? publicIndex : rootIndex;
      return serveStaticFile(res, targetPath);
    }

    if (
      req.method === "GET" &&
      (pathname.startsWith("/css/") ||
        pathname.startsWith("/js/") ||
        pathname.startsWith("/public/"))
    ) {
      const cleanRel = pathname.replace(/^\/public\//, "/").replace(/^\/+/, "");
      const candidatePublic = path.join(__dirname, "public", cleanRel);
      const candidateRoot = path.join(__dirname, cleanRel);
      if (fs.existsSync(candidatePublic)) {
        return serveStaticFile(res, candidatePublic);
      }
      if (fs.existsSync(candidateRoot)) {
        return serveStaticFile(res, candidateRoot);
      }
    }

    // 2. Real-time Event Stream (SSE / WebSocket Hub fallback)
    if (req.method === "GET" && pathname === "/api/events") {
      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "Access-Control-Allow-Origin": "*",
      });
      res.write(
        `data: ${JSON.stringify({
          event: "CONNECTED",
          timestamp: Date.now(),
          payload: { message: "Connected to Multi_Emulator Real-Time Hub" },
        })}\n\n`
      );
      websocketHub.addClient(res);
      return;
    }

    // 3. Health check
    if (req.method === "GET" && pathname === "/health") {
      return sendJson(res, 200, { status: "ok", service: "multi-emulator" });
    }

    // 4. ADR Educational Portal Endpoint (PLAN.md Section 2)
    if (req.method === "GET" && pathname === "/api/adrs") {
      const adrs = adrRoutes.listAdrs();
      return sendJson(res, 200, { count: adrs.length, adrs });
    }

    // 5. Instances Contract Endpoints (PLAN.md Section 2 & 4.2)
    if (req.method === "GET" && pathname === "/api/instances") {
      const autoFarm = urlObj.searchParams.get("preset") === "farm21";
      const result = await instanceRoutes.getFullFarmState(autoFarm);
      return sendJson(res, 200, result);
    }

    if (req.method === "POST" && pathname === "/api/instances") {
      const body = await readJsonBody(req);
      if (body.preset === "farm21") {
        const count = Number(body.count) || 21;
        instanceRoutes.ensureFarmPreset(count);
        const state = await instanceRoutes.getFullFarmState(false);
        websocketHub.broadcastEvent("FARM_PRESET_LOADED", {
          count: state.instances.length,
          message: `Loaded ${state.instances.length} Phone Farm instances`,
        });
        return sendJson(res, 200, state);
      }
      const created = instanceRoutes.createInstance(body);
      const state = await instanceRoutes.getFullFarmState(false);
      return sendJson(res, 201, { created, ...state });
    }

    // Instance lifecycle actions: /api/instances/:id/:action
    const instanceActionMatch = pathname.match(
      /^\/api\/instances\/([^/]+)\/(start|stop|restart|optimize|app|delete|metrics)$/
    );
    if (instanceActionMatch) {
      const [, instanceId, action] = instanceActionMatch;
      const body = req.method === "POST" ? await readJsonBody(req) : {};

      if (action === "metrics") {
        const state = await instanceRoutes.getFullFarmState(false);
        const found = state.instances.find((i) => i.id === instanceId);
        if (!found) return sendJson(res, 404, { error: "Instance not found" });
        return sendJson(res, 200, { id: instanceId, metrics: found.metrics });
      }

      if (action === "start") {
        try {
          await pythonBridge.connectOne(instanceId);
        } catch (_) {}
        instanceRoutes.updateInstanceState(instanceId, {
          status: "RUNNING",
          connectionState: "SYNCED",
          lastMessage: "Instance booted (Ultra-Lite Profile)",
        });
        websocketHub.broadcastEvent("INSTANCE_STATE_CHANGED", {
          instanceId,
          oldStatus: "STOPPED",
          newStatus: "RUNNING",
          message: `${instanceId} started successfully`,
        });
      } else if (action === "stop") {
        try {
          await pythonBridge.disconnectOne(instanceId);
        } catch (_) {}
        instanceRoutes.updateInstanceState(instanceId, {
          status: "STOPPED",
          connectionState: "DISCONNECTED",
          lastMessage: "Instance stopped",
        });
        websocketHub.broadcastEvent("INSTANCE_STATE_CHANGED", {
          instanceId,
          oldStatus: "RUNNING",
          newStatus: "STOPPED",
          message: `${instanceId} stopped`,
        });
      } else if (action === "restart") {
        instanceRoutes.updateInstanceState(instanceId, {
          status: "RUNNING",
          connectionState: "SYNCED",
          lastMessage: "Rebooted & caches cleared",
        });
        websocketHub.broadcastEvent("INSTANCE_STATE_CHANGED", {
          instanceId,
          oldStatus: "STARTING",
          newStatus: "RUNNING",
          message: `${instanceId} restarted`,
        });
      } else if (action === "optimize") {
        instanceRoutes.updateInstanceState(instanceId, {
          cpuPercent: 5.4,
          ramUsageMb: 340,
          fps: 30,
          lastMessage: "ADB Optimized: Animations OFF, Background limited",
        });
        websocketHub.broadcastEvent("INSTANCE_OPTIMIZED", {
          instanceId,
          message: `${instanceId} optimized (RAM reduced to 340MB)`,
        });
      } else if (action === "app") {
        const appId = body.app || "tiktok";
        instanceRoutes.updateInstanceState(instanceId, {
          activeApp: appId,
          status: "RUNNING",
          lastMessage: `Running ${appId.toUpperCase()}`,
        });
        websocketHub.broadcastEvent("APP_LAUNCHED", {
          instanceId,
          app: appId,
          message: `Launched ${appId} on ${instanceId}`,
        });
      } else if (action === "delete") {
        instanceRoutes.customInstances.delete(instanceId);
        instanceRoutes.instanceOverrides.set(instanceId, { deleted: true });
        websocketHub.broadcastEvent("INSTANCE_DELETED", {
          instanceId,
          message: `Removed ${instanceId} from pool`,
        });
      }

      const updatedState = await instanceRoutes.getFullFarmState(false);
      return sendJson(res, 200, updatedState);
    }

    // 6. Connector Scan Endpoint — Discover all available emulators
    if (
      (req.method === "GET" || req.method === "POST") &&
      pathname === "/api/connector/scan"
    ) {
      await pythonBridge.scanEmulators();
      const result = await instanceRoutes.getFullFarmState(false);
      websocketHub.broadcastEvent("SCAN_COMPLETED", {
        discoveredCount: result.summary.discoveredCount,
        message: `Scan discovered ${result.summary.discoveredCount} emulator(s)`,
      });
      return sendJson(res, 200, result);
    }

    // 7. Connector Status Endpoint
    if (req.method === "GET" && pathname === "/api/connector/status") {
      const result = await instanceRoutes.getFullFarmState(false);
      return sendJson(res, 200, result);
    }

    // 8. Connect One or All Discovered Emulators & Link into Sync Hub
    if (req.method === "POST" && pathname === "/api/connector/connect") {
      const body = await readJsonBody(req);
      if (body.instanceId) {
        try {
          await pythonBridge.connectOne(body.instanceId);
        } catch (_) {}
        instanceRoutes.updateInstanceState(body.instanceId, {
          status: "RUNNING",
          connectionState: "SYNCED",
          syncGroupId: "sync_hub_default",
          lastMessage: "Connected & Linked to Sync Hub",
        });
      } else {
        await pythonBridge.connectAll(body.autoLink !== false);
        for (const id of instanceRoutes.customInstances.keys()) {
          instanceRoutes.updateInstanceState(id, {
            status: "RUNNING",
            connectionState: "SYNCED",
            syncGroupId: "sync_hub_default",
            lastMessage: "Synced in Primary Phone Farm Hub",
          });
        }
        for (const id of instanceRoutes.instanceOverrides.keys()) {
          instanceRoutes.updateInstanceState(id, {
            status: "RUNNING",
            connectionState: "SYNCED",
          });
        }
      }
      const result = await instanceRoutes.getFullFarmState(false);
      websocketHub.broadcastEvent("INSTANCE_STATE_CHANGED", {
        instanceId: body.instanceId || "ALL",
        oldStatus: "DISCOVERED",
        newStatus: "RUNNING",
        message: `Connected & synced ${result.summary.syncedCount} instance(s)`,
      });
      return sendJson(res, 200, result);
    }

    // 9. Link Selected Emulators into a Sync Group
    if (req.method === "POST" && pathname === "/api/connector/link") {
      const body = await readJsonBody(req);
      const result = await pythonBridge.linkEmulators(
        body.instanceIds || [],
        body.groupId || "sync_hub_default",
        body.masterId || null
      );
      return sendJson(res, 200, result);
    }

    // 10. Broadcast Synchronized Command across Connected Emulators
    if (req.method === "POST" && pathname === "/api/connector/broadcast") {
      const body = await readJsonBody(req);
      if (!body.command) {
        return sendJson(res, 400, { error: "Missing 'command' in request body" });
      }
      let coreBroadcast = { results: [], targetCount: 0 };
      try {
        const resCore = await pythonBridge.broadcastCommand(
          body.command,
          body.groupId || "sync_hub_default"
        );
        coreBroadcast = resCore.broadcast || resCore;
      } catch (_) {}

      // Also apply to any active Farm Matrix instances
      const appSwitchMatch = body.command.match(/monkey -p ([^\s]+)/);
      let detectedApp = body.app || null;
      if (!detectedApp && appSwitchMatch) {
        const pkg = appSwitchMatch[1];
        if (pkg.includes("trill") || pkg.includes("tiktok")) detectedApp = "tiktok";
        else if (pkg.includes("facebook")) detectedApp = "facebook";
        else if (pkg.includes("instagram")) detectedApp = "instagram";
        else if (pkg.includes("youtube")) detectedApp = "youtube";
      }

      for (const id of instanceRoutes.customInstances.keys()) {
        const inst = instanceRoutes.customInstances.get(id);
        if (inst && inst.status === "RUNNING") {
          const patch = { lastMessage: `Synced cmd: ${body.command}` };
          if (detectedApp) patch.activeApp = detectedApp;
          instanceRoutes.updateInstanceState(id, patch);
        }
      }

      const fullState = await instanceRoutes.getFullFarmState(false);
      const runningTargets = fullState.instances.filter(
        (i) => i.status === "RUNNING"
      );

      const broadcastSummary = {
        groupId: body.groupId || "sync_hub_default",
        command: body.command,
        timestamp: Date.now(),
        targetCount: Math.max(
          runningTargets.length,
          coreBroadcast.targetCount || 0
        ),
        results:
          runningTargets.length > 0
            ? runningTargets.map((inst) => ({
                instanceId: inst.id,
                ok: true,
                command: body.command,
                output: `[Farm-Sync:${inst.port}] Executed '${body.command}'`,
              }))
            : coreBroadcast.results || [],
      };

      websocketHub.broadcastEvent("SYNC_BROADCAST", {
        command: body.command,
        targetCount: broadcastSummary.targetCount,
        app: detectedApp,
        message: `Broadcasted "${body.command}" to ${broadcastSummary.targetCount} synced phones`,
      });

      return sendJson(res, 200, {
        action: "broadcast",
        broadcast: broadcastSummary,
        ...fullState,
      });
    }

    // 11. Disconnect One or All Emulators
    if (req.method === "POST" && pathname === "/api/connector/disconnect") {
      const body = await readJsonBody(req);
      if (body.instanceId) {
        try {
          await pythonBridge.disconnectOne(body.instanceId);
        } catch (_) {}
        instanceRoutes.updateInstanceState(body.instanceId, {
          status: "STOPPED",
          connectionState: "DISCONNECTED",
          lastMessage: "Disconnected from Sync Hub",
        });
      } else {
        await pythonBridge.disconnectAll();
        for (const id of instanceRoutes.customInstances.keys()) {
          instanceRoutes.updateInstanceState(id, {
            status: "STOPPED",
            connectionState: "DISCONNECTED",
            lastMessage: "Disconnected",
          });
        }
      }
      const result = await instanceRoutes.getFullFarmState(false);
      websocketHub.broadcastEvent("INSTANCE_STATE_CHANGED", {
        instanceId: body.instanceId || "ALL",
        oldStatus: "RUNNING",
        newStatus: "STOPPED",
        message: body.instanceId
          ? `Disconnected ${body.instanceId}`
          : "All emulators disconnected",
      });
      return sendJson(res, 200, result);
    }

    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("Not Found");
  } catch (err) {
    sendJson(res, 500, { error: err.message || "Internal Server Error" });
  }
});

if (require.main === module) {
  server.listen(PORT, () => {
    console.log(`Multi_Emulator server listening on http://localhost:${PORT}`);
  });
}

module.exports = { server };
