import React, { memo, useCallback } from 'react';
import { 
  MessageSquare, Image as ImageIcon, Megaphone, Shield, 
  Copy, CheckCircle2, Clock, ExternalLink 
} from 'lucide-react';
import { formatVND } from '../../data/mockDatabase';
import { LiquidCard } from '../../components/common/LiquidCard';
import { Message, MessageStatus, MessageType, MESSAGE_STATUS_CONFIG, MESSAGE_TYPE_LABELS } from '../../types/chat';
import { TransactionStatus } from '../../types';
import { StatusBadge } from './StatusBadge';
import { PublicCodeDisplay, InlinePublicCode } from './PublicCodeDisplay';
import { RecallButton } from './RecallButton';

interface MessageItemProps {
  message: Message;
  isOwn: boolean;
  onRecall: (messageId: string, status: MessageStatus, reason?: string) => void;
  canRecall: boolean;
  isRecalling?: boolean;
  onViewReceipt?: (entryId: string) => void;
}

const MessageItem = memo(function MessageItem({
  message,
  isOwn,
  onRecall,
  canRecall,
  isRecalling,
  onViewReceipt,
}: MessageItemProps) {
  const config = MESSAGE_STATUS_CONFIG[message.status];
  const isReceipt = message.message_type === 'RECEIPT' && message.receipt_data;
  const isAnnouncement = message.message_type === 'ANNOUNCEMENT';
  const isSystem = message.message_type === 'SYSTEM';

  const handleReceiptClick = useCallback(() => {
    if (isReceipt && message.receipt_data?.entry_id && onViewReceipt) {
      onViewReceipt(message.receipt_data.entry_id);
    }
  }, [isReceipt, message.receipt_data?.entry_id, onViewReceipt]);

  // Sender info row
  const renderSenderInfo = () => (
    <div className={`flex items-center gap-2 px-2 text-[11px] ${isOwn ? 'justify-end' : ''}`}>
      {!isOwn && (
        <>
          {message.sender_role === 'MODERATOR' || message.sender_role === 'TREASURER' ? (
            <Shield className="w-3 h-3 text-amber-400" aria-label="Moderator" />
          ) : message.sender_role === 'PUBLIC' ? (
            <span className="w-3 h-3 text-neutral-500" aria-hidden="true">👤</span>
          ) : (
            <span className="w-3 h-3 text-sky-400" aria-hidden="true">👥</span>
          )}
        </>
      )}
      <span className={`font-semibold ${isOwn ? 'text-sky-300' : 'text-neutral-300'}`}>
        {message.sender_name} {isOwn && '(Bạn)'}
      </span>
      {(message.sender_role === 'MODERATOR' || message.sender_role === 'TREASURER') && (
        <span className="px-1.5 py-0.2 rounded-full bg-amber-500/15 text-amber-300 font-bold text-[10px] border border-amber-500/25">
          MOD
        </span>
      )}
      <span className="text-neutral-500 font-mono">{message.created_at}</span>
      {/* Status badge */}
      <StatusBadge status={message.status} size="sm" />
      {/* Public code */}
      {message.public_code && (
        <InlinePublicCode code={message.public_code} />
      )}
    </div>
  );

  // Receipt message card
  const renderReceiptCard = () => {
    const data = message.receipt_data!;
    // Map TransactionStatus to MessageStatus for display
    const statusMap: Record<TransactionStatus, MessageStatus> = {
      'PENDING': 'pending',
      'VERIFIED': 'posted',
      'NEEDS_REVIEW': 'awaiting_review',
      'DUPLICATE': 'rejected',
      'REJECTED': 'rejected',
      'REVERTED': 'recalled',
    };
    const displayStatus = statusMap[data.status] || 'pending';
    const statusColor = MESSAGE_STATUS_CONFIG[displayStatus]?.color || 'neutral';
    const statusIcon = MESSAGE_STATUS_CONFIG[displayStatus]?.icon || 'Clock';

    return (
      <div
        onClick={handleReceiptClick}
        className={`
          max-w-md rounded-2xl p-4 sm:p-5 shadow-xl space-y-3 cursor-pointer 
          transition-all border
          ${isOwn ? 'bg-sky-950/20 border-sky-500/30' : 'apple-card-elevated border-white/15'}
          hover:border-sky-400/40
        `}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && handleReceiptClick()}
        aria-label={`Xem chi tiết biên lai ${data.transaction_code}`}
      >
        <div className="flex items-center justify-between text-xs">
          <span className={`text-${statusColor === 'emerald' ? 'emerald' : statusColor === 'amber' ? 'amber' : 'rose'}-400 font-medium inline-flex items-center gap-1`}>
            <span className="w-3.5 h-3.5 flex items-center justify-center">
              <span className="text-[10px] font-bold">{statusIcon === 'CheckCircle2' ? '✓' : statusIcon === 'AlertTriangle' ? '⚠' : '⏳'}</span>
            </span>
            <span>
              {displayStatus === 'posted' ? 'Đã xác minh AI' : 
               displayStatus === 'awaiting_review' ? 'Cần kiểm tra' : 'Đang xử lý'}
            </span>
          </span>
          <span className="text-neutral-400 font-mono text-[11px]">{data.time}</span>
        </div>

        {/* Embedded Receipt Image */}
        <div className="relative rounded-xl overflow-hidden border border-white/10 aspect-[16/10] bg-black">
          <img
            src={data.image_url}
            alt={`Biên lai ${data.transaction_code}`}
            referrerPolicy="no-referrer"
            className="w-full h-full object-cover"
            loading="lazy"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent flex items-end p-3 justify-between">
            <div>
              <p className="text-[10px] text-neutral-400">Số tiền chuyển:</p>
              <p className="text-lg font-extrabold text-emerald-400 font-tabular">
                +{formatVND(data.amount)}
              </p>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md text-white text-[10px] font-mono border border-white/20">
              {data.transaction_code}
            </span>
          </div>
        </div>

        {message.content && (
          <p className="text-xs text-neutral-200 leading-relaxed">{message.content}</p>
        )}

        <div className="pt-1 flex items-center justify-between text-[11px] text-sky-400">
          <span>Người gửi: {data.sender_name}</span>
          <span className="inline-flex items-center gap-0.5 font-medium">
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
            Chi tiết
          </span>
        </div>

        {/* Recall button for own messages */}
        {isOwn && canRecall && (
          <RecallButton
            messageId={message.id}
            status={message.status}
            canRecall={canRecall}
            onRecall={onRecall}
            isRecalling={isRecalling}
          />
        )}
      </div>
    );
  };

  // Announcement bubble
  const renderAnnouncement = () => (
    <div className="apple-mod-card max-w-lg rounded-2xl p-4 text-white shadow-lg space-y-1">
      <div className="flex items-center gap-1.5 text-xs font-bold text-amber-300">
        <Megaphone className="w-3.5 h-3.5" aria-hidden="true" />
        <span>THÔNG BÁO TỪ BAN CÁN SỰ LỚP</span>
      </div>
      <p className="text-xs sm:text-sm text-neutral-100 leading-relaxed font-medium">
        {message.content}
      </p>
      {message.public_code && (
        <PublicCodeDisplay code={message.public_code} size="sm" />
      )}
    </div>
  );

  // Standard text bubble
  const renderTextBubble = () => (
    <div
      className={`
        max-w-md rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed shadow-sm
        ${isOwn
          ? 'bg-sky-600 text-white rounded-br-sm'
          : 'apple-frosted-glass text-neutral-100 rounded-bl-sm border border-white/10'}
      `}
    >
      {message.content}
    </div>
  );

  // System message
  const renderSystemMessage = () => (
    <div className="w-full text-center py-2">
      <p className="text-xs text-neutral-500 italic">{message.content}</p>
    </div>
  );

  return (
    <div
      className={`flex flex-col ${isOwn ? 'items-end' : 'items-start'} space-y-1`}
      role="article"
      aria-label={`Tin nhắn từ ${message.sender_name}`}
    >
      {(message as any).is_pinned && (
        <LiquidCard variant="mod" clarity="frosted" className="w-full max-w-md rounded-2xl p-4 shadow-xl border border-amber-500/30">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-300 shrink-0">
              <Shield className="w-4 h-4 fill-amber-300/40" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">Thông báo ghim</span>
                <span className="text-[10px] text-neutral-400 font-mono">{message.created_at}</span>
              </div>
              <p className="text-xs sm:text-sm text-neutral-100 font-medium mt-1 leading-relaxed">
                {message.content}
              </p>
            </div>
          </div>
        </LiquidCard>
      )}

      {!(message as any).is_pinned && (
        <>
          {renderSenderInfo()}
          
          {isReceipt ? renderReceiptCard() : 
           isAnnouncement ? renderAnnouncement() : 
           isSystem ? renderSystemMessage() : 
           renderTextBubble()}

          {/* Public code display for text messages */}
          {message.public_code && !isReceipt && !isAnnouncement && !isSystem && (
            <div className={`px-2 ${isOwn ? 'text-right' : ''}`}>
              <PublicCodeDisplay code={message.public_code} size="sm" />
            </div>
          )}

          {/* Recall button for own non-receipt messages */}
          {isOwn && canRecall && !isReceipt && !isAnnouncement && !isSystem && (
            <div className={`px-2 ${isOwn ? 'text-right' : ''}`}>
              <RecallButton
                messageId={message.id}
                status={message.status}
                canRecall={canRecall}
                onRecall={onRecall}
                isRecalling={isRecalling}
              />
            </div>
          )}

          {/* Error message display */}
          {message.error_message && message.status !== 'recalled' && (
            <div className={`px-2 text-[10px] text-rose-400/80 ${isOwn ? 'text-right' : ''}`}>
              {message.error_message}
            </div>
          )}
        </>
      )}
    </div>
  );
});

MessageItem.displayName = 'MessageItem';

export { MessageItem };