/**
 * WebSocket Telemetry Client Manager.
 * Reconnects automatically and dispatches parsed packets to UI components.
 */
class TelemetryClient {
  constructor(wsUrl, onMessageCallback, onStatusChangeCallback) {
    this.wsUrl = wsUrl;
    this.onMessage = onMessageCallback;
    this.onStatusChange = onStatusChangeCallback;
    this.ws = null;
    this.retryInterval = 2000;
    this.isConnected = false;

    this.connect();
  }

  connect() {
    try {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.onopen = () => {
        this.isConnected = true;
        if (this.onStatusChange) this.onStatusChange('CONNECTED', true);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (this.onMessage) this.onMessage(data);
        } catch (e) {
          console.error("Telemetry parse error:", e);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        if (this.onStatusChange) this.onStatusChange('DISCONNECTED', false);
        setTimeout(() => this.connect(), this.retryInterval);
      };

      this.ws.onerror = (err) => {
        this.isConnected = false;
        if (this.onStatusChange) this.onStatusChange('ERROR', false);
      };
    } catch (e) {
      if (this.onStatusChange) this.onStatusChange('FAILED', false);
      setTimeout(() => this.connect(), this.retryInterval);
    }
  }
}

window.TelemetryClient = TelemetryClient;
