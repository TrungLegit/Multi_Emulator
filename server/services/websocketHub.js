/**
 * Real-Time Event & WebSocket Hub (server/services/websocketHub.js)
 * Broadcasts emulator state changes, sync actions, and console logs to connected clients
 * conforming to PLAN.md Section 4.2 WebSocket Event Contract.
 */

const clients = new Set();

/**
 * Register a Server-Sent Events (SSE) / Real-time stream response client
 */
function addClient(res) {
  clients.add(res);
  res.on("close", () => {
    clients.delete(res);
  });
}

/**
 * Broadcast an event payload to all connected UI clients
 * @param {string} eventType e.g. "INSTANCE_STATE_CHANGED", "SYNC_BROADCAST", "LOG_EVENT"
 * @param {object} payload Event payload
 */
function broadcastEvent(eventType, payload = {}) {
  const messageObj = {
    event: eventType,
    timestamp: Date.now(),
    payload,
  };
  const serialized = `data: ${JSON.stringify(messageObj)}\n\n`;
  for (const client of clients) {
    try {
      client.write(serialized);
    } catch (_) {
      clients.delete(client);
    }
  }
  return messageObj;
}

module.exports = {
  addClient,
  broadcastEvent,
  getClientCount: () => clients.size,
};
