import { UserRole, TransactionStatus } from '../types';

export type MessageStatus = 
  | 'pending'
  | 'processing'
  | 'awaiting_review'
  | 'posted'
  | 'rejected'
  | 'failed'
  | 'recalled';

export type MessageType = 'TEXT' | 'RECEIPT' | 'IMAGE' | 'ANNOUNCEMENT' | 'SYSTEM';

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string | null;
  sender_name: string;
  sender_role: UserRole;
  message_type: MessageType;
  content: string;
  attachment_id?: string;
  status: MessageStatus;
  public_code?: string;
  transaction_id?: string;
  error_message?: string;
  created_at: string;
  processed_at?: string;
  // Frontend-only fields
  recall_token?: string;
  is_optimistic?: boolean;
  upload_progress?: number;
  receipt_data?: {
    entry_id: string;
    amount: number;
    transaction_code: string;
    image_url: string;
    status: TransactionStatus;
    sender_name: string;
    uploader_name: string;
    time: string;
  };
}

export interface UploadState {
  id: string;
  file: File;
  preview_url: string;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  upload_id?: string;
  error?: string;
}

export interface MessageCreateRequest {
  conversation_id: string;
  sender_name: string;
  sender_photo?: string;
  message_type: 'TEXT' | 'RECEIPT' | 'IMAGE' | 'ANNOUNCEMENT';
  content: string;
  attachment_ids?: string[];
}

export interface MessageCreateResponse {
  message_id: string;
  public_code: string;
  recall_token: string;
  status: MessageStatus;
  created_at: string;
}

export interface RecallRequest {
  recall_token: string;
  reason: string;
}

export interface RecallResponse {
  message_id: string;
  status: MessageStatus;
  recalled_at: string;
  reversal_transaction_id?: string;
}

export interface MessageStatusResponse {
  message_id: string;
  conversation_id: string;
  sender_name: string;
  sender_role: string;
  message_type: string;
  content: string;
  status: MessageStatus;
  public_code?: string;
  transaction_id?: string;
  error_message?: string;
  created_at: string;
  processed_at?: string;
}

export interface ListMessagesRequest {
  conversation_id: string;
  status?: MessageStatus;
  limit?: number;
  offset?: number;
}

export interface UploadResponse {
  id: string;
  uploader_name: string;
  original_filename: string;
  status: string;
  created_at: string;
}

export interface UploadStatusResponse {
  id: string;
  uploader_name: string;
  original_filename: string;
  status: string;
  created_at: string;
  extracted?: {
    transaction_code?: string;
    amount?: number;
    sender_name?: string;
    bank_name?: string;
    transaction_time?: string;
    confidence?: number;
    status: string;
  };
  transaction_id?: string;
  rejection_reason?: string;
}

export interface PublicFundResponse {
  account_id: string;
  currency: string;
  current_balance: number;
  total_income: number;
  total_expense: number;
}

export interface BankAccountResponse {
  bank_name: string;
  account_name: string;
  account_number: string;
  payment_link?: string;
  qr_image_url?: string;
}

export interface ConversationInfo {
  id: string;
  title: string;
  description?: string;
}

// Status display configuration
export const MESSAGE_STATUS_CONFIG: Record<MessageStatus, {
  label: string;
  icon: string;
  color: 'neutral' | 'sky' | 'amber' | 'emerald' | 'rose';
  animate?: boolean;
  description: string;
}> = {
  pending: {
    label: 'Đang chờ',
    icon: 'Clock',
    color: 'neutral',
    description: 'Tin nhắn vừa được gửi, chờ hệ thống xử lý'
  },
  processing: {
    label: 'Đang xử lý',
    icon: 'Loader2',
    color: 'sky',
    animate: true,
    description: 'AI đang đọc biên lai và đối soát'
  },
  awaiting_review: {
    label: 'Cần duyệt',
    icon: 'AlertTriangle',
    color: 'amber',
    description: 'Cần thủ quỹ kiểm tra thủ công'
  },
  posted: {
    label: 'Đã ghi sổ',
    icon: 'CheckCircle2',
    color: 'emerald',
    description: 'Đã xác thực và ghi vào sổ cái quỹ'
  },
  rejected: {
    label: 'Từ chối',
    icon: 'XCircle',
    color: 'rose',
    description: 'Không hợp lệ (trùng lặp, sai thông tin...)'
  },
  failed: {
    label: 'Lỗi',
    icon: 'AlertCircle',
    color: 'rose',
    description: 'Có lỗi xảy ra khi xử lý'
  },
  recalled: {
    label: 'Đã thu hồi',
    icon: 'RotateCcw',
    color: 'neutral',
    description: 'Người gửi đã thu hồi yêu cầu này'
  }
};

export const MESSAGE_TYPE_LABELS: Record<MessageType, string> = {
  TEXT: 'Tin nhắn',
  RECEIPT: 'Biên lai',
  IMAGE: 'Ảnh',
  ANNOUNCEMENT: 'Thông báo',
  SYSTEM: 'Hệ thống'
};

export const MAX_IMAGES = 5;
export const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
export const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const POLLING_INTERVAL = 5000; // 5 seconds
export const DEFAULT_CONVERSATION_ID = 'classfund_main';