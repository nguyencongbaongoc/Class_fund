import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Send, Image as ImageIcon, X, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { LiquidCard } from '../../components/common/LiquidCard';
import { UploadState } from '../../types/chat';
import { MAX_FILE_SIZE, ALLOWED_MIME_TYPES } from '../../types/chat';

interface ImageUploadAreaProps {
  images: UploadState[];
  onChange: (images: UploadState[]) => void;
  onAddUpload: (file: File) => string;
  onRemoveUpload: (uploadId: string) => void;
  onRetryUpload: (uploadId: string) => void;
  maxFiles?: number;
  disabled?: boolean;
}

export const ImageUploadArea: React.FC<ImageUploadAreaProps> = ({
  images,
  onChange,
  onAddUpload,
  onRemoveUpload,
  onRetryUpload,
  maxFiles = 5,
  disabled = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragOver(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    if (disabled) return;
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, [disabled]);

  const handleClick = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  }, [disabled]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFiles(files);
    // Reset input to allow selecting same file again
    e.target.value = '';
  }, []);

  const handleFiles = useCallback((files: File[]) => {
    if (images.length + files.length > maxFiles) {
      // Could show toast here
      console.warn(`Tối đa ${maxFiles} ảnh`);
      return;
    }

    for (const file of files) {
      // Validate
      if (!ALLOWED_MIME_TYPES.includes(file.type)) {
        console.warn('Chỉ chấp nhận JPEG, PNG, WebP');
        continue;
      }
      if (file.size > MAX_FILE_SIZE) {
        console.warn('File quá lớn (tối đa 5MB)');
        continue;
      }
      
      onAddUpload(file);
    }
  }, [images.length, maxFiles, onAddUpload]);

  const handleRemove = useCallback((uploadId: string) => {
    onRemoveUpload(uploadId);
  }, [onRemoveUpload]);

  const handleRetry = useCallback((uploadId: string) => {
    onRetryUpload(uploadId);
  }, [onRetryUpload]);

  const getStatusIcon = (status: UploadState['status']) => {
    switch (status) {
      case 'pending': return <span className="w-5 h-5 text-neutral-400">⏳</span>;
      case 'uploading': return <Loader2 className="w-5 h-5 text-sky-400 animate-spin" />;
      case 'completed': return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      case 'error': return <AlertCircle className="w-5 h-5 text-rose-400" />;
    }
  };

  const getProgressColor = (status: UploadState['status']) => {
    switch (status) {
      case 'uploading': return 'bg-sky-500';
      case 'completed': return 'bg-emerald-500';
      case 'error': return 'bg-rose-500';
      default: return 'bg-neutral-500';
    }
  };

  return (
    <div className="space-y-3">
      {/* Upload Zone */}
      <div
        ref={fileInputRef as any}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center cursor-pointer transition-all
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          ${isDragOver 
            ? 'border-sky-400 bg-sky-500/10' 
            : 'border-white/20 hover:border-sky-400/50 bg-white/[0.02] hover:bg-white/[0.04]'
          }
        `}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*"
          multiple
          className="hidden"
          disabled={disabled || images.length >= maxFiles}
        />

        {images.length === 0 ? (
          <div className="space-y-3">
            <div className={`
              w-14 h-14 rounded-2xl flex items-center justify-center mx-auto 
              ${isDragOver ? 'bg-sky-500/20 border border-sky-400/30' : 'bg-white/[0.06] border border-white/10'}
              text-sky-400 group-hover:scale-105 transition-transform shadow-lg
            `}>
              <ImageIcon className="w-7 h-7" />
            </div>
            <p className="text-sm font-semibold text-white">
              Kéo thả ảnh biên lai vào đây hoặc <span className="text-sky-400 underline">chọn từ máy</span>
            </p>
            <p className="text-xs text-neutral-400">
              Hỗ trợ PNG, JPG, WebP · Tối đa {maxFiles} ảnh · Mỗi ảnh ≤ 5MB
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-xs font-medium text-neutral-300">
              Đã chọn {images.length}/{maxFiles} ảnh
            </p>
            <p className="text-xs text-neutral-500">
              Bấm để thêm ảnh khác
            </p>
          </div>
        )}

        {/* Upload Progress Summary */}
        {images.some(img => img.status === 'uploading') && (
          <div className="mt-4 p-3 rounded-xl bg-white/[0.03] border border-white/10">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-neutral-300">Đang tải lên...</span>
              <span className="text-sky-400 font-mono">
                {images.filter(i => i.status === 'uploading').length} / {images.length}
              </span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-sky-500 transition-all duration-300"
                style={{
                  width: `${images.reduce((acc, img) => acc + (img.status === 'uploading' ? img.progress : img.status === 'completed' ? 100 : 0), 0) / images.length}%`
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Preview Grid */}
      {images.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3" role="list" aria-label="Ảnh biên lai đã chọn">
          {images.map((upload) => (
            <PreviewItem
              key={upload.id}
              upload={upload}
              onRemove={() => handleRemove(upload.id)}
              onRetry={() => handleRetry(upload.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Preview Item Component
interface PreviewItemProps {
  upload: UploadState;
  onRemove: () => void;
  onRetry: () => void;
}

const PreviewItem: React.FC<PreviewItemProps> = ({ upload, onRemove, onRetry }) => {
  const { progress, status } = upload;

  return (
    <div 
      className={`
        relative group rounded-2xl overflow-hidden border p-1 bg-black/50
        ${status === 'error' ? 'border-rose-500/50' : 'border-white/10'}
        ${status === 'uploading' ? 'ring-2 ring-sky-500/50' : ''}
      `}
      role="listitem"
    >
      {/* Image Preview */}
      <div className="relative aspect-square overflow-hidden rounded-xl">
        {upload.preview_url && (
          <img
            src={upload.preview_url}
            alt={`Ảnh biên lai ${upload.file.name}`}
            className="w-full h-full object-cover transition-opacity"
            style={{ opacity: status === 'uploading' ? 0.7 : 1 }}
          />
        )}

        {/* Status Overlay */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/60 transition-opacity">
          {status === 'pending' && (
            <div className="text-center text-white">
              <div className="w-8 h-8 rounded-full border-2 border-white/30 border-t-white animate-spin mx-auto mb-2" />
              <span className="text-xs">Chờ tải...</span>
            </div>
          )}
          {status === 'uploading' && (
            <div className="text-center text-white">
              <div className="w-10 h-10 rounded-full border-3 border-white/30 border-t-white animate-spin mx-auto mb-2" />
              <span className="text-sm font-medium">{progress}%</span>
            </div>
          )}
          {status === 'completed' && (
            <div className="text-center text-emerald-300">
              <CheckCircle2 className="w-10 h-10 mx-auto mb-2" />
              <span className="text-xs font-medium">Đã tải xong</span>
            </div>
          )}
          {status === 'error' && (
            <div className="text-center text-rose-300 p-2">
              <AlertCircle className="w-8 h-8 mx-auto mb-2" />
              <span className="text-xs">{upload.error || 'Lỗi tải lên'}</span>
            </div>
          )}
        </div>

        {/* Progress Bar */}
        {status === 'uploading' && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/10">
            <div
              className="h-full bg-sky-500 transition-all duration-200"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="absolute inset-0 flex items-end justify-between p-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
        <button
          onClick={onRemove}
          className="pointer-events-auto rounded-full bg-black/70 backdrop-blur text-white p-1.5 hover:bg-rose-500/80 transition-colors"
          aria-label="Xóa ảnh"
          title="Xóa ảnh"
        >
          <X className="w-4 h-4" />
        </button>

        {status === 'error' && (
          <button
            onClick={onRetry}
            className="pointer-events-auto rounded-full bg-sky-500/80 backdrop-blur text-white px-2 py-1.5 text-xs font-medium hover:bg-sky-400 transition-colors"
            aria-label="Thử lại"
            title="Thử lại"
          >
            Thử lại
          </button>
        )}

        {status === 'completed' && (
          <span className="pointer-events-auto rounded-full bg-emerald-500/80 backdrop-blur text-white px-2 py-1.5 text-[10px] font-medium">
            ✓
          </span>
        )}
      </div>

      {/* File Name */}
      <div className="absolute bottom-0 left-0 right-0 p-1.5 bg-gradient-to-t from-black/80 to-transparent text-[10px] text-white/80 truncate">
        {upload.file.name}
      </div>
    </div>
  );
};