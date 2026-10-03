import {
  MessageCreateRequest,
  MessageCreateResponse,
  MessageStatusResponse,
  RecallRequest,
  RecallResponse,
  ListMessagesRequest,
  UploadResponse,
  UploadStatusResponse,
  PublicFundResponse,
  BankAccountResponse,
  MessageStatus,
} from '../types/chat';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.detail || `HTTP ${response.status}`,
      response.status,
      errorData
    );
  }
  return response.json();
}

export const apiClient = {
  // Upload receipt image
  async uploadReceipt(file: File, uploaderName: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('uploader_name', uploaderName);

    const response = await fetch(`${API_BASE}/uploads`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<UploadResponse>(response);
  },

  // Get upload status
  async getUploadStatus(uploadId: string): Promise<UploadStatusResponse> {
    const response = await fetch(`${API_BASE}/uploads/${uploadId}`);
    return handleResponse<UploadStatusResponse>(response);
  },

  // Create message
  async createMessage(data: MessageCreateRequest): Promise<MessageCreateResponse> {
    const response = await fetch(`${API_BASE}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<MessageCreateResponse>(response);
  },

  // Get message status
  async getMessageStatus(messageId: string): Promise<MessageStatusResponse> {
    const response = await fetch(`${API_BASE}/messages/${messageId}`);
    return handleResponse<MessageStatusResponse>(response);
  },

  // Recall message
  async recallMessage(messageId: string, data: RecallRequest): Promise<RecallResponse> {
    const response = await fetch(`${API_BASE}/messages/${messageId}/recall`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<RecallResponse>(response);
  },

  // List messages
  async listMessages(params: ListMessagesRequest): Promise<MessageStatusResponse[]> {
    const searchParams = new URLSearchParams();
    searchParams.set('conversation_id', params.conversation_id);
    if (params.status) searchParams.set('status', params.status);
    if (params.limit) searchParams.set('limit', String(params.limit));
    if (params.offset) searchParams.set('offset', String(params.offset));

    const response = await fetch(`${API_BASE}/messages?${searchParams.toString()}`);
    return handleResponse<MessageStatusResponse[]>(response);
  },

  // Get public fund info
  async getPublicFund(): Promise<PublicFundResponse> {
    const response = await fetch(`${API_BASE}/public/fund`);
    return handleResponse<PublicFundResponse>(response);
  },

  // Get public bank accounts
  async getPublicBankAccounts(): Promise<BankAccountResponse[]> {
    const response = await fetch(`${API_BASE}/public/bank-accounts`);
    return handleResponse<BankAccountResponse[]>(response);
  },
};

// Upload with progress tracking
export async function uploadWithProgress(
  file: File,
  uploaderName: string,
  onProgress: (progress: number) => void
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('uploader_name', uploaderName);

    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        const progress = Math.round((event.loaded / event.total) * 100);
        onProgress(progress);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch {
          reject(new ApiError('Invalid response', xhr.status));
        }
      } else {
        try {
          const errorData = JSON.parse(xhr.responseText);
          reject(new ApiError(errorData.detail || `Upload failed: ${xhr.status}`, xhr.status, errorData));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener('error', () => {
      reject(new ApiError('Network error', 0));
    });

    xhr.addEventListener('abort', () => {
      reject(new ApiError('Upload cancelled', 0));
    });

    xhr.open('POST', `${API_BASE}/uploads`);
    xhr.send(formData);
  });
}

export { ApiError };
export type { ApiError as ApiErrorType };