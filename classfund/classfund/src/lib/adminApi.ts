// Admin API types and client

// Admin Stats
export interface AdminStats {
  currentBalance: number;
  openingBalance: number;
  totalIncome: number;
  totalExpense: number;
  transactionCount: number;
  pendingReviewCount: number;
  processingReviewCount: number;
  workerOnlineCount: number;
  workerTotalCount: number;
  queuePendingCount: number;
  queueProcessingCount: number;
  lastTransactionAt: string | null;
  lastReviewAt: string | null;
}

// Audit Logs
export interface AuditLogItem {
  id: string;
  actorId: string | null;
  actorName: string | null;
  actorRole: string | null;
  action: string;
  entityType: string;
  entityId: string | null;
  beforeData: Record<string, unknown> | null;
  afterData: Record<string, unknown> | null;
  ip: string | null;
  createdAt: string;
}

export interface PaginatedAuditLogs {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
}

// Worker Status
export type WorkerHealth = 'ONLINE' | 'OFFLINE' | 'DEGRADED' | 'UNKNOWN';

export interface WorkerStatus {
  workerId: string;
  status: string;
  modelName: string | null;
  lastHeartbeat: string | null;
  lastProcessedAt: string | null;
  currentJobId: string | null;
  metadata: Record<string, unknown>;
  health: WorkerHealth;
  secondsSinceHeartbeat: number | null;
}

// System Health
export type ComponentStatus = 'HEALTHY' | 'DEGRADED' | 'DOWN' | 'NOT_CONFIGURED';

export interface ComponentHealth {
  name: string;
  status: ComponentStatus;
  lastCheck: string;
  details: string | null;
  latencyMs: number | null;
}

export type SystemHealthOverall = 'HEALTHY' | 'DEGRADED' | 'DOWN' | 'NOT_CONFIGURED';

export interface SystemHealth {
  overall: SystemHealthOverall;
  components: ComponentHealth[];
  checkedAt: string;
}

// Queue Status
export interface QueueStatus {
  pending: number;
  processing: number;
  awaitingReview: number;
  postedToday: number;
  failedToday: number;
  recalledToday: number;
  oldestPendingAgeSeconds: number | null;
  avgProcessingTimeSeconds: number | null;
}

// AI Review Queue
export interface ReviewQueueItem {
  extractionId: string;
  uploadId: string;
  transactionCode: string | null;
  amount: number | null;
  senderName: string | null;
  bankName: string | null;
  transactionTime: string | null;
  confidence: number | null;
  status: string;
  createdAt: string;
  uploaderName: string;
  messageId: string | null;
}

export interface ReviewDetail {
  extractionId: string;
  uploadId: string;
  transactionCode: string | null;
  amount: number | null;
  senderName: string | null;
  bankName: string | null;
  transactionTime: string | null;
  confidence: number | null;
  rawOcr: string | null;
  fieldConfidences: Record<string, number> | null;
  extractionMethod: string | null;
  currency: string | null;
  status: string;
  createdAt: string;
  upload: {
    id: string;
    originalFilename: string;
    uploaderName: string;
    storagePath: string;
    createdAt: string;
  } | null;
  message: {
    id: string;
    content: string;
    senderName: string;
    publicCode: string;
  } | null;
  reviewedBy: string | null;
  reviewedAt: string | null;
  reviewNotes: string | null;
}

export interface ReviewApproveRequest {
  confirm: boolean;
}

export interface ReviewRejectRequest {
  reason: string;
}

export interface ReviewResponse {
  extractionId: string;
  status: string;
  reviewedBy: string;
  reviewedAt: string;
  reviewNotes: string | null;
  transactionId: string | null;
}

// API Client
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

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const adminApi = {
  // Admin Stats
  async getStats(): Promise<AdminStats> {
    const response = await fetch(`${API_BASE}/admin/stats`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<AdminStats>(response);
  },

  // Audit Logs
  async getAuditLogs(params: {
    limit?: number;
    offset?: number;
    action?: string;
    entityType?: string;
    entityId?: string;
    actorId?: string;
    dateFrom?: string;
    dateTo?: string;
  } = {}): Promise<PaginatedAuditLogs> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) searchParams.set(key, String(value));
    });
    const response = await fetch(`${API_BASE}/admin/audit-logs?${searchParams.toString()}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<PaginatedAuditLogs>(response);
  },

  // Export Audit Logs
  async exportAuditLogs(params: {
    action?: string;
    entityType?: string;
    entityId?: string;
    actorId?: string;
    dateFrom?: string;
    dateTo?: string;
    limit?: number;
  } = {}): Promise<{ csv_content: string; total_records: number; filename: string }> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) searchParams.set(key, String(value));
    });
    const response = await fetch(`${API_BASE}/admin/audit-logs/export?${searchParams.toString()}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<{ csv_content: string; total_records: number; filename: string }>(response);
  },

  // Workers
  async getWorkers(): Promise<WorkerStatus[]> {
    const response = await fetch(`${API_BASE}/admin/workers`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<WorkerStatus[]>(response);
  },

  // System Health
  async getHealth(): Promise<SystemHealth> {
    const response = await fetch(`${API_BASE}/admin/health`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<SystemHealth>(response);
  },

  // Queue Status
  async getQueueStatus(): Promise<QueueStatus> {
    const response = await fetch(`${API_BASE}/admin/queue-status`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<QueueStatus>(response);
  },

  // AI Review Queue
  async getReviewQueue(params: {
    status?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<ReviewQueueItem[]> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) searchParams.set(key, String(value));
    });
    const response = await fetch(`${API_BASE}/internal/review?${searchParams.toString()}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<ReviewQueueItem[]>(response);
  },

  async getReviewDetail(extractionId: string): Promise<ReviewDetail> {
    const response = await fetch(`${API_BASE}/internal/review/${extractionId}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<ReviewDetail>(response);
  },

  async approveExtraction(extractionId: string, confirm: boolean): Promise<ReviewResponse> {
    const response = await fetch(`${API_BASE}/internal/review/${extractionId}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ confirm }),
    });
    return handleResponse<ReviewResponse>(response);
  },

  async rejectExtraction(extractionId: string, reason: string): Promise<ReviewResponse> {
    const response = await fetch(`${API_BASE}/internal/review/${extractionId}/reject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ reason }),
    });
    return handleResponse<ReviewResponse>(response);
  },

  // Get original image for review
  getImageUrl(uploadId: string): string {
    return `${API_BASE}/internal/ai/uploads/${uploadId}/file`;
  },
};

export { ApiError };