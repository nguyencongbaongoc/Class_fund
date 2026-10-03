import { MessageStatusResponse, MessageStatus } from '../types/chat';

type MessageUpdateCallback = (message: MessageStatusResponse) => void;
type ConnectionStatusCallback = (connected: boolean) => void;

interface RealtimeAdapterConfig {
  conversationId: string;
  onMessageUpdate: MessageUpdateCallback;
  onConnectionChange?: ConnectionStatusCallback;
  supabaseUrl?: string;
  supabaseAnonKey?: string;
}

export class RealtimeAdapter {
  private channel: unknown = null;
  private isConnected = false;
  private config: RealtimeAdapterConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(config: RealtimeAdapterConfig) {
    this.config = config;
  }

  async connect(): Promise<boolean> {
    const supabaseUrl = this.config.supabaseUrl || import.meta.env.VITE_SUPABASE_URL;
    const supabaseAnonKey = this.config.supabaseAnonKey || import.meta.env.VITE_SUPABASE_ANON_KEY;

    if (!supabaseUrl || !supabaseAnonKey) {
      console.warn('[Realtime] Supabase credentials not configured');
      this.config.onConnectionChange?.(false);
      return false;
    }

    try {
      // Dynamic import to avoid bundle size if not used
      const { createClient } = await import('@supabase/supabase-js');
      const supabase = createClient(supabaseUrl, supabaseAnonKey);

      this.channel = supabase
        .channel(`messages:${this.config.conversationId}`)
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'messages',
            filter: `conversation_id=eq.${this.config.conversationId}`,
          },
          (payload) => this.handleRealtimeEvent(payload)
        )
        .subscribe((status) => {
          if (status === 'SUBSCRIBED') {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.config.onConnectionChange?.(true);
            console.log('[Realtime] Connected to messages channel');
          } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
            this.handleDisconnect();
          }
        });

      return true;
    } catch (error) {
      console.error('[Realtime] Failed to connect:', error);
      this.config.onConnectionChange?.(false);
      return false;
    }
  }

  private handleRealtimeEvent(payload: {
    eventType: 'INSERT' | 'UPDATE' | 'DELETE';
    new: Record<string, unknown>;
    old: Record<string, unknown>;
  }) {
    if (payload.eventType === 'DELETE') return;

    const message = payload.new as unknown as MessageStatusResponse;
    
    // Only process messages that are in progress or terminal states
    const relevantStatuses: MessageStatus[] = [
      'pending',
      'processing',
      'awaiting_review',
      'posted',
      'rejected',
      'failed',
      'recalled',
    ];

    if (relevantStatuses.includes(message.status as MessageStatus)) {
      this.config.onMessageUpdate(message);
    }
  }

  private handleDisconnect() {
    this.isConnected = false;
    this.config.onConnectionChange?.(false);

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`[Realtime] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('[Realtime] Max reconnect attempts reached');
    }
  }

  disconnect() {
    if (this.channel) {
      try {
        // @ts-ignore - supabase channel has unsubscribe method
        this.channel.unsubscribe();
      } catch (e) {
        console.warn('[Realtime] Error unsubscribing:', e);
      }
      this.channel = null;
    }
    this.isConnected = false;
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
  }

  get connected(): boolean {
    return this.isConnected;
  }
}

// Factory function for easier usage
export function createRealtimeAdapter(config: RealtimeAdapterConfig): RealtimeAdapter {
  return new RealtimeAdapter(config);
}