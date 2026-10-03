import { UploadState, UploadResponse } from '../types/chat';
import { apiClient, uploadWithProgress, ApiError } from './api';

export interface UploadAdapterConfig {
  onProgress: (uploadId: string, progress: number) => void;
  onComplete: (uploadId: string, result: UploadResponse) => void;
  onError: (uploadId: string, error: string) => void;
}

export class UploadAdapter {
  private config: UploadAdapterConfig;
  private abortControllers = new Map<string, AbortController>();

  constructor(config: UploadAdapterConfig) {
    this.config = config;
  }

  async uploadFile(file: File, uploaderName: string): Promise<string> {
    const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Validate file
    const validationError = this.validateFile(file);
    if (validationError) {
      this.config.onError(uploadId, validationError);
      throw new Error(validationError);
    }

    const abortController = new AbortController();
    this.abortControllers.set(uploadId, abortController);

    try {
      const result = await uploadWithProgress(
        file,
        uploaderName,
        (progress) => this.config.onProgress(uploadId, progress)
      );
      
      this.config.onComplete(uploadId, result);
      return result.id;
    } catch (error) {
      if (error instanceof ApiError && error.status === 0) {
        // Network error or aborted
        throw error;
      }
      const message = error instanceof Error ? error.message : 'Upload failed';
      this.config.onError(uploadId, message);
      throw error;
    } finally {
      this.abortControllers.delete(uploadId);
    }
  }

  async uploadFiles(files: File[], uploaderName: string): Promise<string[]> {
    const uploadIds: string[] = [];
    
    for (const file of files) {
      try {
        const uploadId = await this.uploadFile(file, uploaderName);
        uploadIds.push(uploadId);
      } catch (error) {
        // Continue with other files
        console.error('[UploadAdapter] Failed to upload file:', error);
      }
    }
    
    return uploadIds;
  }

  cancelUpload(uploadId: string) {
    const controller = this.abortControllers.get(uploadId);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(uploadId);
    }
  }

  cancelAll() {
    for (const controller of this.abortControllers.values()) {
      controller.abort();
    }
    this.abortControllers.clear();
  }

  private validateFile(file: File): string | null {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const maxSize = 5 * 1024 * 1024; // 5MB

    if (!allowedTypes.includes(file.type)) {
      return 'Chỉ chấp nhận file ảnh JPEG, PNG hoặc WebP';
    }

    if (file.size > maxSize) {
      return `File quá lớn (tối đa 5MB). File hiện tại: ${(file.size / 1024 / 1024).toFixed(1)}MB`;
    }

    return null;
  }

  // Create preview URL for a file
  static createPreviewUrl(file: File): string {
    return URL.createObjectURL(file);
  }

  // Revoke preview URL to free memory
  static revokePreviewUrl(url: string): void {
    URL.revokeObjectURL(url);
  }
}

export function createUploadAdapter(config: UploadAdapterConfig): UploadAdapter {
  return new UploadAdapter(config);
}