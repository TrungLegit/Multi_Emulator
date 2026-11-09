#!/usr/bin/env node
/**
 * Multi_Emulator — Node.js Backend Orchestrator & Connector API Server
 * Educational Multi Emulator ADR version
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const pythonBridge = require("./server/services/pythonBridge");

const PORT = process.env.PORT || 3000;

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

const server = http.createServer(async (req, res) => {
  const urlObj = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  const pathname = urlObj.pathname;

  try {
    // 1. Static Frontend Dashboard
    if (req.method === "GET" && (pathname === "/" || pathname === "/index.html")) {
      const filePath = path.join(__dirname, "index.html");
      fs.readFile(filePath, "utf8", (err, content) => {
        if (err) {
          res.writeHead(500, { "Content-Type": "text/plain" });
          res.end("Internal Server Error");
          return;
        }
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        res.end(content);
      });
      return;
    }

    // 2. Health check
    if (req.method === "GET" && pathname === "/health") {
      return sendJson(res, 200, { status: "ok", service: "multi-emulator" });
    }

    // 3. Instances Contract Endpoint (PLAN.md Section 2 & 4.2)
    if (req.method === "GET" && pathname === "/api/instances") {
      const result = await pythonBridge.getStatus();
      return sendJson(res, 200, result);
    }

    // 4. Connector Scan Endpoint — Discover all available emulators
    if (
      (req.method === "GET" || req.method === "POST") &&
      pathname === "/api/connector/scan"
    ) {
      const result = await pythonBridge.scanEmulators();
      return sendJson(res, 200, result);
    }

    // 5. Connector Status Endpoint
    if (req.method === "GET" && pathname === "/api/connector/status") {
      const result = await pythonBridge.getStatus();
      return sendJson(res, 200, result);
    }

    // 6. Connect One or All Discovered Emulators & Link into Sync Hub
    if (req.method === "POST" && pathname === "/api/connector/connect") {
      const body = await readJsonBody(req);
      const result = body.instanceId
        ? await pythonBridge.connectOne(body.instanceId)
        : await pythonBridge.connectAll(body.autoLink !== false);
      return sendJson(res, 200, result);
    }

    // 7. Link Selected Emulators into a Sync Group
    if (req.method === "POST" && pathname === "/api/connector/link") {
      const body = await readJsonBody(req);
      const result = await pythonBridge.linkEmulators(
        body.instanceIds || [],
        body.groupId || "sync_hub_default",
        body.masterId || null
      );
      return sendJson(res, 200, result);
    }

    // 8. Broadcast Synchronized Command across Connected Emulators
    if (req.method === "POST" && pathname === "/api/connector/broadcast") {
      const body = await readJsonBody(req);
      if (!body.command) {
        return sendJson(res, 400, { error: "Missing 'command' in request body" });
      }
      const result = await pythonBridge.broadcastCommand(
        body.command,
        body.groupId || "sync_hub_default"
      );
      return sendJson(res, 200, result);
    }

    // 9. Disconnect One or All Emulators
    if (req.method === "POST" && pathname === "/api/connector/disconnect") {
      const body = await readJsonBody(req);
      const result = body.instanceId
        ? await pythonBridge.disconnectOne(body.instanceId)
        : await pythonBridge.disconnectAll();
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
