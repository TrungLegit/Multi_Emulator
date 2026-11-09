/**
 * Real-Time Event Stream & WebSocket Client (public/js/websocket.js)
 * Deliverable for Chương — Frontend Engineer & Interactive Dashboard Lead
 * Connects to Backend SSE/WebSocket hub and triggers live UI updates without page reload.
 */

export class RealtimeClient {
  constructor({ onEvent, onStatusChange } = {}) {
    this.onEvent = onEvent || (() => {});
    this.onStatusChange = onStatusChange || (() => {});
    this.eventSource = null;
  }

  connect() {
    if (typeof window === "undefined" || !("EventSource" in window)) {
      this.onStatusChange(false, "Polling Mode");
      return;
    }

    try {
      this.eventSource = new EventSource("/api/events");

      this.eventSource.onopen = () => {
        this.onStatusChange(true, "Real-Time Sync Live");
      };

      this.eventSource.onmessage = (evt) => {
        try {
          const parsed = JSON.parse(evt.data);
          this.onEvent(parsed);
        } catch (_) {
          // Ignore malformed keepalive frames
        }
      };

      this.eventSource.onerror = () => {
        this.onStatusChange(false, "Reconnecting...");
      };
    } catch (_) {
      this.onStatusChange(false, "Offline");
    }
  }
}
