/** Error classification and retry utilities for message submission. */
export enum ErrorClassification {
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT = 'TIMEOUT',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTH_ERROR = 'AUTH_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  CONFLICT = 'CONFLICT',
  RATE_LIMITED = 'RATE_LIMITED',
  SERVER_ERROR = 'SERVER_ERROR',
  UNKNOWN = 'UNKNOWN',
}

export enum RetryDecision {
  RETRY = 'RETRY',
  NO_RETRY = 'NO_RETRY',
  RECONCILE = 'RECONCILE',
}

export interface ErrorInfo {
  classification: ErrorClassification;
  statusCode: number | null;
  message: string;
  retryAfter: number | null;
  isRetryable: boolean;
  shouldReconcile: boolean;
}

export interface RetryConfig {
  maxRetries: number;
  initialDelay: number; // seconds
  maxDelay: number; // seconds
  exponentialBase: number;
  jitter: number; // 0-1
  retryOnTimeout: boolean;
  reconcileOnTimeout: boolean;
}

export interface RetryState {
  attempt: number;
  lastError: ErrorInfo | null;
  idempotencyKey: string | null;
  isReconciling: boolean;
}

export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelay: 1.0,
  maxDelay: 30.0,
  exponentialBase: 2.0,
  jitter: 0.1,
  retryOnTimeout: true,
  reconcileOnTimeout: true,
};

export function classifyError(
  error: Error,
  statusCode: number | null = null,
  retryAfter: number | null = null
): ErrorInfo {
  // Network/connection errors
  if (error instanceof TypeError && error.message.includes('NetworkError')) {
    return {
      classification: ErrorClassification.NETWORK_ERROR,
      statusCode,
      message: error.message,
      retryAfter,
      isRetryable: true,
      shouldReconcile: false,
    };
  }

  // Timeout detection
  if (error instanceof DOMException && error.name === 'TimeoutError') {
    return {
      classification: ErrorClassification.TIMEOUT,
      statusCode,
      message: error.message,
      retryAfter,
      isRetryable: true,
      shouldReconcile: true,
    };
  }

  if (error.message.includes('timeout') || error.message.includes('Timeout')) {
    return {
      classification: ErrorClassification.TIMEOUT,
      statusCode,
      message: error.message,
      retryAfter,
      isRetryable: true,
      shouldReconcile: true,
    };
  }

  // Network error detection
  if (error.message.toLowerCase().includes('network') || 
      error.message.toLowerCase().includes('connection') ||
      error.message.toLowerCase().includes('fetch')) {
    return {
      classification: ErrorClassification.NETWORK_ERROR,
      statusCode,
      message: error.message,
      retryAfter,
      isRetryable: true,
      shouldReconcile: false,
    };
  }

  // HTTP status code classification
  if (statusCode !== null) {
    if (statusCode === 400) {
      return {
        classification: ErrorClassification.VALIDATION_ERROR,
        statusCode,
        message: error.message,
        retryAfter,
        isRetryable: false,
        shouldReconcile: false,
      };
    }
    if (statusCode === 401 || statusCode === 403) {
      return {
        classification: ErrorClassification.AUTH_ERROR,
        statusCode,
        message: error.message,
        retryAfter,
        isRetryable: false,
        shouldReconcile: false,
      };
    }
    if (statusCode === 404) {
      return {
        classification: ErrorClassification.NOT_FOUND,
        statusCode,
        message: error.message,
        retryAfter,
        isRetryable: false,
        shouldReconcile: false,
      };
    }
    if (statusCode === 409) {
      return {
        classification: ErrorClassification.CONFLICT,
        statusCode,
        message: error.message,
        retryAfter,
        isRetryable: false,
        shouldReconcile: false,
      };
    }
    if (statusCode === 429) {
      return {
        classification: ErrorClassification.RATE_LIMITED,
        statusCode,
        message: error.message,
        retryAfter,
        isRetryable: true,
        shouldReconcile: false,
      };
    }
    if (statusCode >= 500 && statusCode < 600) {
      return {
        classification: ErrorClassification.SERVER_ERROR,
        statusCode,
        message: error.message,
        retryAfter,
        isRetryable: true,
        shouldReconcile: false,
      };
    }
  }

  // Unknown error
  return {
    classification: ErrorClassification.UNKNOWN,
    statusCode,
    message: error.message,
    retryAfter,
    isRetryable: false,
    shouldReconcile: false,
  };
}

export function calculateBackoff(attempt: number, config: Partial<RetryConfig> = {}): number {
  const mergedConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let delay = Math.min(
    mergedConfig.initialDelay * Math.pow(mergedConfig.exponentialBase, attempt),
    mergedConfig.maxDelay
  );

  // Add jitter
  const jitterAmount = delay * mergedConfig.jitter;
  delay = delay + Math.random() * jitterAmount * 2 - jitterAmount;

  return Math.max(0, delay);
}

export interface RetryState {
  attempt: number;
  lastError: ErrorInfo | null;
  idempotencyKey: string | null;
  isReconciling: boolean;
}

export function shouldRetry(
  errorInfo: ErrorInfo,
  state: RetryState,
  config: RetryConfig
): RetryDecision {
  if (state.attempt >= config.maxRetries) {
    return RetryDecision.NO_RETRY;
  }

  if (!errorInfo.isRetryable) {
    return RetryDecision.NO_RETRY;
  }

  // For timeout/unknown server errors, try to reconcile first
  if (errorInfo.shouldReconcile && !state.isReconciling) {
    return RetryDecision.RECONCILE;
  }

  return RetryDecision.RETRY;
}