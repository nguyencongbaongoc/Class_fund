import { useState, useCallback, useEffect, useRef } from 'react';
import { 
  Message, 
  MessageStatus, 
  MessageCreateRequest, 
  MessageCreateResponse,
  MessageStatusResponse,
  DEFAULT_CONVERSATION_ID,
  MESSAGE_STATUS_CONFIG
} from '../types/chat';
import { apiClient } from '../lib/api';
import { createHybridAdapter, HybridAdapter } from '../lib/polling';
import { createRecallAdapter, RecallAdapter, createSessionStorageRecallConfig } from '../lib/recall';
import { createUploadAdapter, UploadAdapter } from '../lib/upload';
import { UploadState } from '../types/chat';
import { 
  classifyError, 
  calculateBackoff, 
  shouldRetry, 
  RetryConfig, 
  RetryState, 
  RetryDecision,
  ErrorInfo,
  DEFAULT_RETRY_CONFIG
} from '../lib/retry';

interface UseChatConfig {
  conversationId?: string;
  currentUserRole: 'PUBLIC' | 'MEMBER' | 'MODERATOR' | 'TREASURER';
  currentUserName: string;
}

interface UseChatReturn {
  // State
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
  connectionSource: 'realtime' | 'polling' | null;
  
  // Upload state
  uploads: Map<string, UploadState>;
  
  // Actions
  sendMessage: (data: Omit<MessageCreateRequest, 'conversation_id'>) => Promise<MessageCreateResponse | null>;
  recallMessage: (messageId: string, reason?: string) => Promise<void>;
  addUpload: (file: File) => string;
  removeUpload: (uploadId: string) => void;
  retryUpload: (uploadId: string) => void;
  refreshMessages: () => Promise<void>;
  
  // Computed
  getMessage: (id: string) => Message | undefined;
  canRecall: (message: Message) => boolean;
  getStatusLabel: (status: MessageStatus) => string;
  getStatusColor: (status: MessageStatus) => string;
}

export function useChat(config: UseChatConfig): UseChatReturn {
  const {
    conversationId = DEFAULT_CONVERSATION_ID,
    currentUserRole,
    currentUserName,
  } = config;

  // Core state
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionSource, setConnectionSource] = useState<'realtime' | 'polling' | null>(null);
  
  // Upload state
  const [uploads, setUploads] = useState<Map<string, UploadState>>(new Map());
  
  // Adapters
  const hybridAdapterRef = useRef<HybridAdapter | null>(null);
  const recallAdapterRef = useRef<RecallAdapter | null>(null);
  const uploadAdapterRef = useRef<UploadAdapter | null>(null);
  
  // Initialize adapters
  useEffect(() => {
    // Hybrid adapter for realtime + polling
    hybridAdapterRef.current = createHybridAdapter({
      conversationId,
      onMessageUpdate: handleMessageUpdate,
      onConnectionChange: (connected, source) => {
        setIsConnected(connected);
        setConnectionSource(source);
      },
      supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
      supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY,
      pollingInterval: 5000,
    });

    // Recall adapter with sessionStorage
    const recallConfig = createSessionStorageRecallConfig();
    recallAdapterRef.current = createRecallAdapter({
      ...recallConfig,
      onRecallSuccess: (messageId, response) => {
        updateMessageStatus(messageId, response.status, {
          processed_at: response.recalled_at,
          error_message: response.reversal_transaction_id ? undefined : response.status === 'recalled' ? 'Đã thu hồi bởi người gửi' : undefined,
        });
      },
      onRecallError: (messageId, error) => {
        // Error is handled in recallMessage
        console.error('[useChat] Recall error:', error);
      },
    });

    // Upload adapter
    uploadAdapterRef.current = createUploadAdapter({
      onProgress: (uploadId, progress) => {
        setUploads(prev => {
          const next = new Map(prev);
          const upload = next.get(uploadId);
          if (upload) {
            next.set(uploadId, { ...upload, progress, status: 'uploading' });
          }
          return next;
        });
      },
      onComplete: (uploadId, result) => {
        setUploads(prev => {
          const next = new Map(prev);
          const upload = next.get(uploadId);
          if (upload) {
            next.set(uploadId, { 
              ...upload, 
              progress: 100, 
              status: 'completed', 
              upload_id: result.id 
            });
          }
          return next;
        });
      },
      onError: (uploadId, error) => {
        setUploads(prev => {
          const next = new Map(prev);
          const upload = next.get(uploadId);
          if (upload) {
            next.set(uploadId, { ...upload, status: 'error', error });
          }
          return next;
        });
      },
    });

    // Connect hybrid adapter
    hybridAdapterRef.current.connect();

    // Load initial messages
    refreshMessages();

    return () => {
      hybridAdapterRef.current?.disconnect();
      uploadAdapterRef.current?.cancelAll();
    };
  }, [conversationId]);

  // Handle realtime/polling message updates
  const handleMessageUpdate = useCallback((message: MessageStatusResponse) => {
    setMessages(prev => {
      const index = prev.findIndex(m => m.id === message.message_id);
      const updatedMessage: Message = {
        id: message.message_id,
        conversation_id: message.conversation_id,
        sender_id: null,
        sender_name: message.sender_name,
        sender_role: message.sender_role as Message['sender_role'],
        message_type: message.message_type as Message['message_type'],
        content: message.content,
        status: message.status as MessageStatus,
        public_code: message.public_code,
        transaction_id: message.transaction_id,
        error_message: message.error_message,
        created_at: message.created_at,
        processed_at: message.processed_at,
        attachment_ids: message.attachment_ids,
        is_optimistic: false,
      };

      if (index >= 0) {
        // Preserve recall_token and other frontend fields
        const existing = prev[index];
        const merged = {
          ...updatedMessage,
          recall_token: existing.recall_token,
          is_optimistic: false,
        };
        const next = [...prev];
        next[index] = merged;
        return next;
      } else {
        // New message from realtime (shouldn't happen for our own messages)
        hybridAdapterRef.current?.addMessageId(message.message_id);
        return [updatedMessage, ...prev];
      }
    });
  }, []);

  // Update message status helper
  const updateMessageStatus = useCallback((
    messageId: string, 
    status: MessageStatus, 
    extra: Partial<Message> = {}
  ) => {
    setMessages(prev => {
      const index = prev.findIndex(m => m.id === messageId);
      if (index === -1) return prev;
      
      const next = [...prev];
      next[index] = { ...next[index], status, ...extra };
      
      // Manage hybrid adapter message tracking
      const terminalStatuses: MessageStatus[] = ['posted', 'rejected', 'failed', 'recalled'];
      if (terminalStatuses.includes(status)) {
        hybridAdapterRef.current?.removeMessageId(messageId);
      } else {
        hybridAdapterRef.current?.addMessageId(messageId);
      }
      
      return next;
    });
  }, []);

  // Send message with retry logic and idempotency
  const sendMessage = useCallback(async (
    data: Omit<MessageCreateRequest, 'conversation_id'>
  ): Promise<MessageCreateResponse | null> => {
    setError(null);
    
    // Generate stable idempotency key for this logical submission
    const idempotencyKey = `msg_${conversationId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Retry state
    const retryState: RetryState = {
      attempt: 0,
      idempotencyKey,
      lastError: null,
      isReconciling: false,
    };
    
    const retryConfig: RetryConfig = {
      maxRetries: 3,
      initialDelay: 1.0,
      maxDelay: 30.0,
      exponentialBase: 2.0,
      jitter: 0.1,
      retryOnTimeout: true,
      reconcileOnTimeout: true,
    };
    
    // Prepare request once (same payload for all retries)
    let attachmentIds: string[] = [];
    const uploadIds = Array.from(uploads.entries())
      .filter(([, u]) => u.status === 'completed' && u.upload_id)
      .map(([, u]) => u.upload_id!);
    
    if (uploadIds.length > 0) {
      attachmentIds = uploadIds;
    }
    
    const request: MessageCreateRequest = {
      conversation_id: conversationId,
      ...data,
      attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined,
    };
    
    // Add idempotency key to request if backend supports it
    // For now, we track it locally for reconciliation
    
    while (true) {
      try {
        const response = await apiClient.createMessage(request);
        
        // Store recall token
        recallAdapterRef.current?.storeRecallToken(response.message_id, response.recall_token);
        
        // Add optimistic message
        const optimisticMessage: Message = {
          id: response.message_id,
          conversation_id: conversationId,
          sender_id: null,
          sender_name: data.sender_name,
          sender_role: currentUserRole,
          message_type: data.message_type,
          content: data.content,
          attachment_id: attachmentIds[0],
          attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined,
          status: response.status,
          public_code: response.public_code,
          created_at: response.created_at,
          recall_token: response.recall_token,
          is_optimistic: true,
        };
        
        setMessages(prev => [optimisticMessage, ...prev]);
        hybridAdapterRef.current?.addMessageId(response.message_id);
        
        // Clear completed uploads
        setUploads(prev => {
          const next = new Map(prev);
          for (const uploadId of uploadIds) {
            for (const [key, value] of next.entries()) {
              if (value.upload_id === uploadId) {
                next.delete(key);
                break;
              }
            }
          }
          return next;
        });
        
        return response;
        
      } catch (err) {
        // Classify error and decide retry
        let statusCode: number | undefined;
        let retryAfter: number | undefined;
        
        if (err && typeof err === 'object' && 'status' in err) {
          statusCode = (err as any).status;
        }
        
        const errorInfo = classifyError(err as Error, statusCode, retryAfter);
        retryState.lastError = errorInfo;
        
        const decision = shouldRetry(errorInfo, retryState, retryConfig);
        
        if (decision === RetryDecision.RECONCILE) {
          // Timeout - try to reconcile by checking if message was created
          // For now, we'll just retry once for reconciliation
          if (!retryState.isReconciling) {
            retryState.isReconciling = true;
            retryState.attempt++;
            const delay = calculateBackoff(retryState.attempt, retryConfig);
            await new Promise(resolve => setTimeout(resolve, delay * 1000));
            continue;
          }
        }
        
        if (decision === RetryDecision.RETRY) {
          retryState.attempt++;
          const delay = calculateBackoff(retryState.attempt, retryConfig);
          await new Promise(resolve => setTimeout(resolve, delay * 1000));
          continue;
        }
        
        // No retry - set error and return
        const message = err instanceof Error ? err.message : 'Gửi tin nhắn thất bại';
        setError(message);
        return null;
      }
    }
  }, [conversationId, currentUserRole, uploads]);

  // Recall message
  const recallMessage = useCallback(async (
    messageId: string, 
    reason?: string
  ) => {
    if (!recallAdapterRef.current) return;
    
    try {
      // Get the message to determine its status
      const message = messages.find(m => m.id === messageId);
      if (!message) return;
      
      await recallAdapterRef.current.recallMessage(messageId, message.status, reason);
    } catch (err) {
      // Error already handled in adapter
      console.error('[useChat] Recall failed:', err);
    }
  }, [messages]);

  // Upload management
  const addUpload = useCallback((file: File): string => {
    const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const previewUrl = UploadAdapter.createPreviewUrl(file);
    
    const uploadState: UploadState = {
      id: uploadId,
      file,
      preview_url: previewUrl,
      progress: 0,
      status: 'pending',
    };

    setUploads(prev => {
      const next = new Map(prev);
      next.set(uploadId, uploadState);
      return next;
    });

    // Start upload
    const uploaderName = currentUserRole === 'PUBLIC' 
      ? localStorage.getItem('guest_sender_name') || currentUserName 
      : currentUserName;
    
    uploadAdapterRef.current?.uploadFile(file, uploaderName).catch(() => {
      // Error handled in adapter
    });

    return uploadId;
  }, [currentUserRole, currentUserName]);

  const removeUpload = useCallback((uploadId: string) => {
    setUploads(prev => {
      const next = new Map(prev);
      const upload = next.get(uploadId);
      if (upload) {
        UploadAdapter.revokePreviewUrl(upload.preview_url);
        uploadAdapterRef.current?.cancelUpload(uploadId);
      }
      next.delete(uploadId);
      return next;
    });
  }, []);

  const retryUpload = useCallback((uploadId: string) => {
    setUploads(prev => {
      const upload = prev.get(uploadId);
      if (!upload || upload.status !== 'error') return prev;
      
      const next = new Map(prev);
      next.set(uploadId, { ...upload, status: 'pending', error: undefined, progress: 0 });
      
      const uploaderName = currentUserRole === 'PUBLIC' 
        ? localStorage.getItem('guest_sender_name') || currentUserName 
        : currentUserName;
      
      uploadAdapterRef.current?.uploadFile(upload.file, uploaderName).catch(() => {
        // Error handled in adapter
      });
      
      return next;
    });
  }, [currentUserRole, currentUserName]);

  // Refresh messages from server
  const refreshMessages = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const serverMessages = await apiClient.listMessages({ 
        conversation_id: conversationId, 
        limit: 50 
      });
      
      const mappedMessages: Message[] = serverMessages.map(m => ({
        id: m.message_id,
        conversation_id: m.conversation_id,
        sender_id: null,
        sender_name: m.sender_name,
        sender_role: m.sender_role as Message['sender_role'],
        message_type: m.message_type as Message['message_type'],
        content: m.content,
        status: m.status as MessageStatus,
        public_code: m.public_code,
        transaction_id: m.transaction_id,
        error_message: m.error_message,
        created_at: m.created_at,
        processed_at: m.processed_at,
        attachment_ids: m.attachment_ids,
        is_optimistic: false,
        recall_token: recallAdapterRef.current?.getStoredRecallToken(m.message_id) || undefined,
      }));
      
      setMessages(mappedMessages);
      
      // Track non-terminal messages for polling
      const activeMessageIds = mappedMessages
        .filter(m => !['posted', 'rejected', 'failed', 'recalled'].includes(m.status))
        .map(m => m.id);
      
      // Add message IDs to hybrid adapter
      activeMessageIds.forEach(id => hybridAdapterRef.current?.addMessageId(id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Không thể tải tin nhắn';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId]);

  // Helpers
  const getMessage = useCallback((id: string) => {
    return messages.find(m => m.id === id);
  }, [messages]);

  const canRecall = useCallback((message: Message) => {
    return recallAdapterRef.current?.canRecall(message.status, message.id) ?? false;
  }, []);

  const getStatusLabel = useCallback((status: MessageStatus) => {
    return MESSAGE_STATUS_CONFIG[status]?.label || status;
  }, []);

  const getStatusColor = useCallback((status: MessageStatus) => {
    return MESSAGE_STATUS_CONFIG[status]?.color || 'neutral';
  }, []);

  return {
    messages,
    isLoading,
    error,
    isConnected,
    connectionSource,
    uploads,
    sendMessage,
    recallMessage,
    addUpload,
    removeUpload,
    retryUpload,
    refreshMessages,
    getMessage,
    canRecall,
    getStatusLabel,
    getStatusColor,
  };
}

// Re-export UploadAdapter for static methods
export { UploadAdapter };