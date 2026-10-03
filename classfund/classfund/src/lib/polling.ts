import { MessageStatusResponse, MessageStatus } from '../types/chat';

type PollingCallback = (messages: MessageStatusResponse[]) => void;

interface PollingAdapterConfig {
  conversationId: string;
  messageIds: string[];
  onUpdate: PollingCallback;
  interval?: number;
  enabled?: boolean;
}

export class PollingAdapter {
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private config: PollingAdapterConfig;
  private isRunning = false;
  private lastFetchedAt = new Map<string, string>();

  constructor(config: PollingAdapterConfig) {
    this.config = {
      interval: 5000,
      enabled: true,
      ...config,
    };
  }

  start() {
    if (this.isRunning) return;
    if (!this.config.enabled) return;

    this.isRunning = true;
    this.poll(); // Initial poll
    this.intervalId = setInterval(() => this.poll(), this.config.interval);
    console.log('[Polling] Started polling for messages');
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isRunning = false;
    console.log('[Polling] Stopped polling');
  }

  setMessageIds(messageIds: string[]) {
    this.config.messageIds = messageIds;
  }

  setEnabled(enabled: boolean) {
    this.config.enabled = enabled;
    if (enabled && !this.isRunning) {
      this.start();
    } else if (!enabled && this.isRunning) {
      this.stop();
    }
  }

  private async poll() {
    if (!this.isRunning || this.config.messageIds.length === 0) return;

    try {
      // Only poll for messages that are not in terminal states
      const messageIdsToPoll = this.config.messageIds.filter(id => {
        const lastFetched = this.lastFetchedAt.get(id);
        // Don't poll too frequently for the same message
        // But always poll if we haven't fetched recently
        return true; // Let backend handle caching
      });

      if (messageIdsToPoll.length === 0) return;

      // Fetch status for each message
      // In a real implementation, you might batch this
      const updates: MessageStatusResponse[] = [];

      for (const messageId of messageIdsToPoll) {
        try {
          const response = await fetch(`/api/v1/messages/${messageId}`);
          if (response.ok) {
            const message = await response.json();
            this.lastFetchedAt.set(messageId, message.processed_at || message.created_at);
            
            // Only notify if status changed or is in progress
            if (this.isRelevantStatus(message.status)) {
              updates.push(message);
            }
            
            // Stop polling for terminal states
            if (this.isTerminalStatus(message.status)) {
              this.config.messageIds = this.config.messageIds.filter(id => id !== messageId);
            }
          }
        } catch (error) {
          console.warn(`[Polling] Failed to fetch message ${messageId}:`, error);
        }
      }

      if (updates.length > 0) {
        this.config.onUpdate(updates);
      }

      // Stop if no more messages to poll
      if (this.config.messageIds.length === 0) {
        this.stop();
      }
    } catch (error) {
      console.error('[Polling] Poll error:', error);
    }
  }

  private isRelevantStatus(status: string): boolean {
    const relevantStatuses: MessageStatus[] = [
      'pending',
      'processing',
      'awaiting_review',
      'posted',
      'rejected',
      'failed',
      'recalled',
    ];
    return relevantStatuses.includes(status as MessageStatus);
  }

  private isTerminalStatus(status: string): boolean {
    const terminalStatuses: MessageStatus[] = [
      'posted',
      'rejected',
      'failed',
      'recalled',
    ];
    return terminalStatuses.includes(status as MessageStatus);
  }

  get running(): boolean {
    return this.isRunning;
  }
}

export function createPollingAdapter(config: PollingAdapterConfig): PollingAdapter {
  return new PollingAdapter(config);
}

// Hybrid adapter that uses both realtime and polling
import { RealtimeAdapter } from './realtime';

export interface HybridAdapterConfig {
  conversationId: string;
  onMessageUpdate: (message: MessageStatusResponse) => void;
  onConnectionChange?: (connected: boolean, source: 'realtime' | 'polling') => void;
  supabaseUrl?: string;
  supabaseAnonKey?: string;
  pollingInterval?: number;
}

export class HybridAdapter {
  private realtime: RealtimeAdapter;
  private polling: PollingAdapter;
  private messageIds = new Set<string>();
  private usePollingFallback = false;
  private config: HybridAdapterConfig;

  constructor(config: HybridAdapterConfig) {
    this.config = config;
    this.realtime = new RealtimeAdapter({
      conversationId: config.conversationId,
      onMessageUpdate: (message) => this.handleRealtimeUpdate(message),
      onConnectionChange: (connected) => this.handleRealtimeConnectionChange(connected, config),
      supabaseUrl: config.supabaseUrl,
      supabaseAnonKey: config.supabaseAnonKey,
    });

    this.polling = new PollingAdapter({
      conversationId: config.conversationId,
      messageIds: [],
      onUpdate: (messages) => this.handlePollingUpdate(messages),
      interval: config.pollingInterval || 5000,
      enabled: false, // Start disabled, enable if realtime fails
    });
  }

  async connect() {
    const realtimeConnected = await this.realtime.connect();
    
    if (!realtimeConnected) {
      console.log('[Hybrid] Realtime unavailable, starting polling fallback');
      this.usePollingFallback = true;
      this.polling.setEnabled(true);
      this.config.onConnectionChange?.(true, 'polling');
    }
  }

  private handleRealtimeUpdate(message: MessageStatusResponse) {
    this.messageIds.add(message.message_id);
    this.config.onMessageUpdate(message);
  }

  private handlePollingUpdate(messages: MessageStatusResponse[]) {
    for (const message of messages) {
      this.messageIds.add(message.message_id);
      this.config.onMessageUpdate(message);
    }
    // Sync message IDs to polling
    this.polling.setMessageIds(Array.from(this.messageIds));
  }

  private handleRealtimeConnectionChange(connected: boolean, config: HybridAdapterConfig) {
    if (!connected && !this.usePollingFallback) {
      console.log('[Hybrid] Realtime disconnected, enabling polling fallback');
      this.usePollingFallback = true;
      this.polling.setMessageIds(Array.from(this.messageIds));
      this.polling.setEnabled(true);
      config.onConnectionChange?.(true, 'polling');
    } else if (connected && this.usePollingFallback) {
      console.log('[Hybrid] Realtime reconnected, disabling polling');
      this.usePollingFallback = false;
      this.polling.setEnabled(false);
      config.onConnectionChange?.(true, 'realtime');
    } else {
      config.onConnectionChange?.(connected, this.usePollingFallback ? 'polling' : 'realtime');
    }
  }

  addMessageId(messageId: string) {
    this.messageIds.add(messageId);
    if (this.usePollingFallback) {
      this.polling.setMessageIds(Array.from(this.messageIds));
    }
  }

  removeMessageId(messageId: string) {
    this.messageIds.delete(messageId);
    if (this.usePollingFallback) {
      this.polling.setMessageIds(Array.from(this.messageIds));
    }
  }

  disconnect() {
    this.realtime.disconnect();
    this.polling.stop();
  }

  get isUsingRealtime(): boolean {
    return this.realtime.connected && !this.usePollingFallback;
  }

  get isUsingPolling(): boolean {
    return this.usePollingFallback && this.polling.running;
  }
}

export function createHybridAdapter(config: HybridAdapterConfig): HybridAdapter {
  return new HybridAdapter(config);
}