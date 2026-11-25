/**
 * Telemetry Client for PROJECT W.A.L.L.
 * Handles dual WebSocket streaming (30Hz) and REST polling fallback.
 */

export class TelemetryClient {
  constructor(options = {}) {
    this.wsUrl = options.wsUrl || 'ws://localhost:8000/ws';
    this.restUrl = options.restUrl || 'http://localhost:8000/api/telemetry';
    this.onTelemetry = options.onTelemetry || (() => {});
    this.onStatusChange = options.onStatusChange || (() => {});

    this.socket = null;
    this.isConnected = false;
    this.pollingInterval = null;

    this.connect();
  }

  connect() {
    try {
      this.socket = new WebSocket(this.wsUrl);

      this.socket.onopen = () => {
        this.isConnected = true;
        this.onStatusChange('CONNECTED', 'connected');
        if (this.pollingInterval) {
          clearInterval(this.pollingInterval);
          this.pollingInterval = null;
        }
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onTelemetry(data);
        } catch (e) {
          console.error('Failed to parse telemetry frame:', e);
        }
      };

      this.socket.onerror = (err) => {
        console.warn('WebSocket connection error, starting REST fallback...', err);
        this.handleDisconnect();
      };

      this.socket.onclose = () => {
        this.handleDisconnect();
      };
    } catch (e) {
      this.handleDisconnect();
    }
  }

  handleDisconnect() {
    this.isConnected = false;
    this.onStatusChange('REST POLLING', 'error');

    // Start fallback REST polling if not already running
    if (!this.pollingInterval) {
      this.pollingInterval = setInterval(async () => {
        try {
          const res = await fetch(this.restUrl);
          if (res.ok) {
            const data = await res.json();
            this.onTelemetry(data);
          }
        } catch (err) {
          // server might still be booting
        }
      }, 100);
    }

    // Try reconnecting WebSocket after 3 seconds
    setTimeout(() => {
      if (!this.isConnected) {
        this.connect();
      }
    }, 3000);
  }
}

