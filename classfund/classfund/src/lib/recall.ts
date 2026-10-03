import { RecallRequest, RecallResponse, MessageStatus } from '../types/chat';
import { apiClient, ApiError } from './api';

const RECALL_TOKEN_STORAGE_KEY = 'classfund_recall_tokens';

export interface RecallAdapterConfig {
  onRecallSuccess: (messageId: string, response: RecallResponse) => void;
  onRecallError: (messageId: string, error: string) => void;
  getRecallToken: (messageId: string) => string | null;
  setRecallToken: (messageId: string, token: string) => void;
  removeRecallToken: (messageId: string) => void;
}

export class RecallAdapter {
  private config: RecallAdapterConfig;
  private pendingRecalls = new Set<string>();

  constructor(config: RecallAdapterConfig) {
    this.config = config;
  }

  // Check if a message can be recalled
  canRecall(messageStatus: MessageStatus, messageId: string): boolean {
    // Can recall if:
    // 1. Message is in a recallable state
    // 2. We have the recall token
    const recallableStates: MessageStatus[] = [
      'pending',
      'processing',
      'awaiting_review',
      'posted', // Can recall posted messages (creates reversal)
    ];

    const hasToken = !!this.config.getRecallToken(messageId);
    const isPending = this.pendingRecalls.has(messageId);

    return recallableStates.includes(messageStatus) && hasToken && !isPending;
  }

  // Get recall reason based on status
  getDefaultRecallReason(status: MessageStatus): string {
    switch (status) {
      case 'pending':
      case 'processing':
      case 'awaiting_review':
        return 'Người gửi hủy yêu cầu trước khi xử lý';
      case 'posted':
        return 'Người gửi yêu cầu thu hồi sau khi đã ghi sổ';
      default:
        return 'Người gửi thu hồi';
    }
  }

  async recallMessage(messageId: string, status: MessageStatus, customReason?: string): Promise<RecallResponse | null> {
    // Check if already recalling
    if (this.pendingRecalls.has(messageId)) {
      throw new Error('Recall already in progress');
    }

    // Get recall token
    const recallToken = this.config.getRecallToken(messageId);
    if (!recallToken) {
      const error = 'Không tìm thấy mã thu hồi. Không thể thu hồi tin nhắn này.';
      this.config.onRecallError(messageId, error);
      throw new Error(error);
    }

    // Determine reason
    const reason = customReason || this.getDefaultRecallReason(status);

    // Mark as pending
    this.pendingRecalls.add(messageId);

    try {
      const response = await apiClient.recallMessage(messageId, {
        recall_token: recallToken,
        reason,
      });

      // Remove token after successful recall
      this.config.removeRecallToken(messageId);
      this.pendingRecalls.delete(messageId);

      this.config.onRecallSuccess(messageId, response);
      return response;
    } catch (error) {
      this.pendingRecalls.delete(messageId);
      
      let errorMessage = 'Thu hồi thất bại';
      if (error instanceof ApiError) {
        switch (error.status) {
          case 403:
            errorMessage = 'Không có quyền thu hồi: mã không hợp lệ hoặc đã hết hạn';
            break;
          case 409:
            errorMessage = error.data && typeof error.data === 'object' && 'detail' in error.data
              ? String(error.data.detail)
              : 'Tin nhắn đã được thu hồi hoặc mã đã được sử dụng';
            break;
          case 404:
            errorMessage = 'Không tìm thấy tin nhắn';
            break;
          case 500:
            errorMessage = 'Lỗi máy chủ khi tạo bút toán đảo';
            break;
          default:
            errorMessage = error.message;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }

      this.config.onRecallError(messageId, errorMessage);
      throw new Error(errorMessage);
    }
  }

  isRecalling(messageId: string): boolean {
    return this.pendingRecalls.has(messageId);
  }

  // Store recall token when message is created
  storeRecallToken(messageId: string, token: string): void {
    this.config.setRecallToken(messageId, token);
  }

  // Get stored recall token
  getStoredRecallToken(messageId: string): string | null {
    return this.config.getRecallToken(messageId);
  }

  // Clear recall token (after successful recall or cleanup)
  clearRecallToken(messageId: string): void {
    this.config.removeRecallToken(messageId);
  }
}

// Default storage implementation using sessionStorage
export function createSessionStorageRecallConfig(): Pick<RecallAdapterConfig, 
  'getRecallToken' | 'setRecallToken' | 'removeRecallToken'
> {
  return {
    getRecallToken: (messageId: string): string | null => {
      try {
        const data = sessionStorage.getItem(RECALL_TOKEN_STORAGE_KEY);
        if (!data) return null;
        const tokens = JSON.parse(data) as Record<string, string>;
        return tokens[messageId] || null;
      } catch {
        return null;
      }
    },

    setRecallToken: (messageId: string, token: string): void => {
      try {
        const data = sessionStorage.getItem(RECALL_TOKEN_STORAGE_KEY);
        const tokens = data ? JSON.parse(data) : {};
        tokens[messageId] = token;
        sessionStorage.setItem(RECALL_TOKEN_STORAGE_KEY, JSON.stringify(tokens));
      } catch (error) {
        console.error('[RecallAdapter] Failed to store recall token:', error);
      }
    },

    removeRecallToken: (messageId: string): void => {
      try {
        const data = sessionStorage.getItem(RECALL_TOKEN_STORAGE_KEY);
        if (!data) return;
        const tokens = JSON.parse(data) as Record<string, string>;
        delete tokens[messageId];
        sessionStorage.setItem(RECALL_TOKEN_STORAGE_KEY, JSON.stringify(tokens));
      } catch (error) {
        console.error('[RecallAdapter] Failed to remove recall token:', error);
      }
    },
  };
}

export function createRecallAdapter(config: RecallAdapterConfig): RecallAdapter {
  return new RecallAdapter(config);
}