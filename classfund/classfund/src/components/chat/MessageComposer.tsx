import React, { useState, useRef, useCallback, useEffect, FormEvent } from 'react';
import { Send, Image as ImageIcon, X, Loader2, Smile } from 'lucide-react';
import { LiquidCard } from '../../components/common/LiquidCard';
import { UserRole, MessageType } from '../../types';
import { ImageUploadArea } from './ImageUploadArea';
import { SenderNameInput, InlineSenderNameInput } from './SenderNameInput';
import { StatusBadge } from './StatusBadge';
import { UploadState } from '../../types/chat';

import { MessageCreateRequest } from '../../types/chat';

interface MessageComposerProps {
  currentUser: {
    id: string;
    name: string;
    role: UserRole;
  };
  onSend: (data: Omit<MessageCreateRequest, 'conversation_id'>) => Promise<void>;
  isSending: boolean;
  uploads: Map<string, UploadState>;
  onAddUpload: (file: File) => string;
  onRemoveUpload: (uploadId: string) => void;
  onRetryUpload: (uploadId: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  currentUser,
  onSend,
  isSending,
  uploads,
  onAddUpload,
  onRemoveUpload,
  onRetryUpload,
  disabled = false,
  placeholder = 'Gửi tin nhắn thảo luận...',
}) => {
  const [inputText, setInputText] = useState('');
  const [senderName, setSenderName] = useState('');
  const [isModAnnouncement, setIsModAnnouncement] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isPublic = currentUser.role === 'PUBLIC';
  const requiresSenderName = isPublic;
  const canSend = (inputText.trim() || uploads.size > 0) && 
    (!requiresSenderName || senderName.trim().length >= 2) && 
    !isSending && 
    !disabled;

  // Load saved sender name for public users
  useEffect(() => {
    if (isPublic && !senderName) {
      const saved = localStorage.getItem('guest_sender_name');
      if (saved) {
        setSenderName(saved);
      }
    }
  }, [isPublic, senderName]);

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 150);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputText, adjustTextareaHeight]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSend) return;

    const messageType: MessageType = isModAnnouncement ? 'ANNOUNCEMENT' : 
      uploads.size > 0 ? 'IMAGE' : 'TEXT';

    const attachmentIds = Array.from(uploads.values())
      .filter(u => u.status === 'completed' && u.upload_id)
      .map(u => u.upload_id!);

    await onSend({
      content: inputText.trim() || (uploads.size > 0 ? 'Đã gửi ảnh biên lai' : ''),
      message_type: messageType,
      sender_name: requiresSenderName ? senderName.trim() : currentUser.name,
      attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined,
    });

    setInputText('');
    setIsModAnnouncement(false);
    textareaRef.current?.focus();
  };

  const handleImageClick = () => {
    fileInputRef.current?.click();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSend) {
        handleSubmit(e);
      }
    }
  };

  const hasPendingUploads = Array.from(uploads.values()).some(u => u.status === 'uploading');
  const hasErrors = Array.from(uploads.values()).some(u => u.status === 'error');

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Sender name input for guests */}
      {requiresSenderName && (
        <InlineSenderNameInput
          value={senderName}
          onChange={setSenderName}
          required={true}
          className="w-full"
        />
      )}

      {/* Mod announcement toggle */}
      {(currentUser.role === 'MODERATOR' || currentUser.role === 'TREASURER') && (
        <div className="flex items-center gap-2 px-1">
          <label className="flex items-center gap-1.5 text-xs text-amber-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isModAnnouncement}
              onChange={(e) => setIsModAnnouncement(e.target.checked)}
              disabled={isSending || disabled}
              className="rounded border-amber-400 text-amber-500 focus:ring-0 disabled:opacity-50"
            />
            <span className="font-semibold">Đăng dưới dạng Thông báo Moderator [MOD]</span>
          </label>
        </div>
      )}

      {/* Composer input area */}
      <div className="relative">
        <div className="flex items-end gap-2 p-1.5 rounded-full bg-neutral-900/80 backdrop-blur-2xl border border-white/15 shadow-2xl">
          {/* Image attachment button */}
          <div className="relative">
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                const files = Array.from(e.target.files || []);
                for (const file of files) {
                  onAddUpload(file);
                }
                e.target.value = '';
              }}
              accept="image/*"
              multiple
              className="hidden"
              disabled={disabled || isSending || uploads.size >= 5}
            />
            <button
              type="button"
              onClick={handleImageClick}
              disabled={disabled || isSending || uploads.size >= 5}
              className="w-9 h-9 rounded-full bg-white/[0.06] hover:bg-white/[0.12] flex items-center justify-center text-sky-400 hover:text-white transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
              title="Đính kèm ảnh biên lai"
              aria-label="Đính kèm ảnh biên lai"
            >
              <ImageIcon className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isSending}
            rows={1}
            className={`
              flex-1 min-h-[44px] max-h-[150px] bg-transparent px-3 py-2.5 
              text-xs sm:text-sm text-white placeholder-neutral-500 
              focus:outline-none resize-none
              ${requiresSenderName && !senderName.trim() ? 'placeholder:text-rose-400' : ''}
            `}
            aria-label="Nội dung tin nhắn"
            aria-describedby={requiresSenderName ? 'sender-name-hint' : undefined}
          />

          {/* Emoji button */}
          <button
            type="button"
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            className="w-9 h-9 rounded-full bg-white/[0.06] hover:bg-white/[0.12] flex items-center justify-center text-neutral-400 hover:text-white transition-all active:scale-95"
            aria-label="Chèn biểu cảm"
          >
            <Smile className="w-4 h-4" aria-hidden="true" />
          </button>

          {/* Send button */}
          <button
            type="submit"
            disabled={!canSend}
            className={`
              min-h-[44px] px-5 rounded-full font-medium text-xs flex items-center gap-1.5 
              shadow-md active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed
              ${isSending || hasPendingUploads 
                ? 'bg-neutral-600 text-neutral-300' 
                : 'apple-btn-primary text-white'
              }
            `}
            aria-label={isSending ? 'Đang gửi...' : hasPendingUploads ? 'Đang tải ảnh...' : 'Gửi tin nhắn'}
          >
            {isSending || hasPendingUploads ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                <span>{isSending ? 'Đang gửi...' : 'Đang tải ảnh...'}</span>
              </>
            ) : (
              <>
                <span>Gửi</span>
                <Send className="w-3.5 h-3.5" aria-hidden="true" />
              </>
            )}
          </button>
        </div>

        {/* Upload preview area */}
        {uploads.size > 0 && (
          <ImageUploadArea
            images={Array.from(uploads.values())}
            onChange={() => {}} // State managed by parent
            onAddUpload={onAddUpload}
            onRemoveUpload={onRemoveUpload}
            onRetryUpload={onRetryUpload}
            maxFiles={5}
            disabled={disabled || isSending}
          />
        )}

        {/* Status indicators */}
        {(hasPendingUploads || hasErrors) && (
          <div className="flex items-center gap-3 px-2 text-xs">
            {hasPendingUploads && (
              <StatusBadge status="processing" size="sm" showLabel showIcon />
            )}
            {hasErrors && (
              <span className="text-rose-400 flex items-center gap-1">
                <X className="w-3 h-3" aria-hidden="true" />
                Có ảnh tải lên thất bại
              </span>
            )}
          </div>
        )}

        {/* Emoji picker placeholder */}
        {showEmojiPicker && (
          <div className="absolute bottom-full left-0 right-0 mb-2 p-3 rounded-2xl bg-neutral-900/95 backdrop-blur-xl border border-white/10 shadow-2xl animate-in fade-in">
            <p className="text-center text-sm text-neutral-400">Bảng biểu cảm sẽ được thêm ở phiên bản sau</p>
          </div>
        )}
      </div>

      {/* Validation hint */}
      {requiresSenderName && !senderName.trim() && inputText.trim() && (
        <p className="text-[10px] text-rose-400/80 flex items-center gap-1 px-1">
          <X className="w-3 h-3" aria-hidden="true" />
          Vui lòng nhập tên của bạn trước khi gửi
        </p>
      )}
    </form>
  );
};

// Simplified composer for inline use
export const SimpleMessageComposer: React.FC<{
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
  onAttachImage?: () => void;
}> = ({ value, onChange, onSend, disabled, placeholder, onAttachImage }) => {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) onSend();
    }
  };

  return (
    <div className="flex items-center gap-2 p-1.5 rounded-full bg-neutral-900/80 backdrop-blur-2xl border border-white/15">
      {onAttachImage && (
        <button
          type="button"
          onClick={onAttachImage}
          disabled={disabled}
          className="w-9 h-9 rounded-full bg-white/[0.06] hover:bg-white/[0.12] flex items-center justify-center text-sky-400 hover:text-white transition-all disabled:opacity-40"
          aria-label="Đính kèm ảnh"
        >
          <ImageIcon className="w-4 h-4" aria-hidden="true" />
        </button>
      )}
      
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="flex-1 bg-transparent px-3 py-2 text-sm text-white placeholder-neutral-500 focus:outline-none resize-none min-h-[44px]"
        aria-label="Tin nhắn"
      />
      
      <button
        type="button"
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="min-h-[44px] px-4 rounded-full apple-btn-primary font-medium text-xs flex items-center gap-1.5 shadow-md disabled:opacity-40"
      >
        <span>Gửi</span>
        <Send className="w-3.5 h-3.5" aria-hidden="true" />
      </button>
    </div>
  );
};