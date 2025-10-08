const WS_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/^http/, 'ws') || 'ws://127.0.0.1:8000';

class WebSocketClient {
  private ws: WebSocket | null = null;
  private onMessageHandler: ((message: any) => void) | null = null;

  connect(orchardId: string, sessionId: string) {
    const url = `${WS_BASE_URL}/api/v1/orchards/${orchardId}/diagnosis/${sessionId}/ws`;
    
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log("WebSocket is already connected.");
      return;
    }

    console.log('[WS] connecting', url);
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('[WS] connected');
    };

    this.ws.onmessage = (event) => {
      if (typeof event?.data === 'string') {
        const head = event.data.slice(0, 60);
        console.log('[WS] recv', head);
      }
      if (this.onMessageHandler) {
        this.onMessageHandler(event.data);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WS] error', error);
    };

    this.ws.onclose = (e) => {
      console.warn('[WS] closed', e?.code, e?.reason);
      // TODO: reconnection with backoff if needed
    };
  }

  setOnMessageHandler(handler: (message: any) => void) {
    this.onMessageHandler = handler;
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const wsClient = new WebSocketClient();
