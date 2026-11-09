/**
 * Node.js <-> Python Core IPC Bridge (ADR-002)
 * Calls the Python Connector CLI with `--json` using child_process.execFile
 * so the Node.js event loop is never blocked.
 */

const { execFile } = require("child_process");
const path = require("path");

const ROOT_DIR = path.resolve(__dirname, "../..");
const MAIN_PY = path.join(ROOT_DIR, "main.py");
const PYTHON_BIN = process.env.PYTHON_BIN || "python3";

/**
 * Execute a Python Connector command and return parsed JSON output.
 * @param {string[]} args CLI arguments passed to main.py
 * @returns {Promise<object>}
 */
function runPythonConnector(args = []) {
  return new Promise((resolve, reject) => {
    const fullArgs = [MAIN_PY, "--json", ...args];
    execFile(
      PYTHON_BIN,
      fullArgs,
      { cwd: ROOT_DIR, timeout: 20000 },
      (error, stdout, stderr) => {
        if (error) {
          return reject(
            new Error(
              `Python Connector failed (${error.message}): ${stderr || stdout}`
            )
          );
        }
        try {
          const parsed = JSON.parse(stdout.trim());
          resolve(parsed);
        } catch (parseErr) {
          reject(
            new Error(`Invalid JSON from Python Core: ${stdout || stderr}`)
          );
        }
      }
    );
  });
}

module.exports = {
  runPythonConnector,
  scanEmulators: () => runPythonConnector(["scan"]),
  getStatus: () => runPythonConnector(["status"]),
  connectAll: (autoLink = true) =>
    runPythonConnector(
      autoLink ? ["connect", "--all"] : ["connect", "--all", "--no-link"]
    ),
  connectOne: (instanceId) =>
    runPythonConnector(["connect", "--id", String(instanceId)]),
  linkEmulators: (ids = [], group = "sync_hub_default", master = null) => {
    const args = ["link", "--group", group];
    if (Array.isArray(ids) && ids.length > 0) {
      args.push("--ids", ...ids.map(String));
    }
    if (master) {
      args.push("--master", String(master));
    }
    return runPythonConnector(args);
  },
  broadcastCommand: (cmd, group = "sync_hub_default") =>
    runPythonConnector(["broadcast", "--cmd", String(cmd), "--group", group]),
  disconnectOne: (instanceId) =>
    runPythonConnector(["disconnect", "--id", String(instanceId)]),
  disconnectAll: () => runPythonConnector(["disconnect"]),

  // Browser Profile & Anti-Lag Multi-Control
  createBrowserProfiles: (count = 1, prefix = "profile", browserType = "auto") =>
    runPythonConnector([
      "profile-create",
      "--count",
      String(count),
      "--prefix",
      prefix,
      "--type",
      browserType,
    ]),
  startBrowserProfile: (id = null, url = "about:blank") =>
    runPythonConnector(
      id
        ? ["profile-start", "--id", String(id), "--url", url]
        : ["profile-start", "--all", "--url", url]
    ),
  stopBrowserProfile: (id = null) =>
    runPythonConnector(
      id ? ["profile-stop", "--id", String(id)] : ["profile-stop", "--all"]
    ),
  listBrowserProfiles: () => runPythonConnector(["profile-list"]),
  syncBrowserAction: (cmd, group = "sync_hub_default") =>
    runPythonConnector(["profile-sync", "--cmd", String(cmd), "--group", group]),
};
