import React, { useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { ViewTab } from '../types';
import { LiquidCard } from '../components/common/LiquidCard';
import { Message, MessageStatus, DEFAULT_CONVERSATION_ID, MessageCreateRequest } from '../types/chat';
import { 
  MessageList, 
  MessageComposer, 
  EmptyState, 
  LoadingState,
  StatusBadge 
} from '../components/chat';
import { useChat } from '../hooks/useChat';
import { formatVND } from '../data/mockDatabase';
import { UploadState } from '../types/chat';
import { Sparkles, Shield, Info, AlertTriangle } from 'lucide-react';

export const GuestChatPage: React.FC = () => {
  const { 
    currentUser, 
    currentTab, 
    setCurrentTab, 
    ledgerEntries, 
    setSelectedTransaction,
    addToast 
  } = useApp();

  // Check if we're in guest mode
  const isGuest = currentUser.role === 'PUBLIC';
  const conversationId = DEFAULT_CONVERSATION_ID;

  // Use the chat hook
  const {
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
    canRecall,
    getStatusLabel,
    getStatusColor,
  } = useChat({
    conversationId,
    currentUserRole: currentUser.role,
    currentUserName: currentUser.name,
  });

  // Find pinned message
  const pinnedMessage = messages.find(m => (m as any).is_pinned);

  // Handle receipt click - navigate to ledger detail
  const handleViewReceipt = useCallback((entryId: string) => {
    const matchedEntry = ledgerEntries.find(e => e.id === entryId);
    if (matchedEntry) {
      setSelectedTransaction(matchedEntry);
    } else {
      // For guest messages that haven't been posted yet
      addToast({
        type: 'info',
        title: 'Chưa có trong sổ cái',
        description: 'Biên lai này đang được xử lý hoặc chưa được ghi sổ.',
      });
    }
  }, [ledgerEntries, setSelectedTransaction, addToast]);

  // Handle recall
  const handleRecall = useCallback(async (messageId: string, reason?: string) => {
    await recallMessage(messageId, reason);
  }, [recallMessage]);

  // Handle send message
  const handleSend = useCallback(async (data: Omit<MessageCreateRequest, 'conversation_id'>) => {
    await sendMessage(data);
  }, [sendMessage]);

  // Header info for guests
  const renderGuestHeader = () => {
    if (!isGuest) return null;

    return (
      <LiquidCard variant="clear" clarity="clear" className="p-4 mb-4 border border-sky-500/20 bg-sky-500/5">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-sky-500/20 border border-sky-500/30 flex items-center justify-center shrink-0">
            <Info className="w-5 h-5 text-sky-400" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-bold text-sky-300">Chế độ Khách (Guest)</h3>
            <p className="text-xs text-neutral-300 mt-1 leading-relaxed">
              Bạn đang tham gia thảo luận với tư cách khách. Tin nhắn và ảnh biên lai bạn gửi sẽ được AI xử lý 
              và cần thủ quỹ xác thực trước khi ghi vào sổ cái quỹ.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-2 py-1 rounded-full bg-sky-500/20 text-sky-300 text-[10px] font-medium border border-sky-500/30">
                Mã tham chiếu: CF-YYYYMMDD-XXXXXX
              </span>
              <span className="px-2 py-1 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-medium border border-amber-500/30">
                Có thể THU HỘI trước khi ghi sổ
              </span>
              <span className="px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-medium border border-emerald-500/30">
                AI đọc biên lai tự động
              </span>
            </div>
          </div>
        </div>
      </LiquidCard>
    );
  };

  // Connection status indicator
  const renderConnectionStatus = () => {
    if (!isConnected) return null;

    return (
      <div className="fixed bottom-24 right-4 z-20 animate-in slide-in-from-right">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-medium shadow-lg">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" aria-hidden="true" />
          <span>
            {connectionSource === 'realtime' ? 'Realtime' : 'Polling'} đang kết nối
          </span>
        </div>
      </div>
    );
  };

  // Error display
  const renderError = () => {
    if (!error) return null;

    return (
      <LiquidCard variant="elevated" clarity="frosted" className="p-4 mb-4 border border-rose-500/30 bg-rose-500/10">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" aria-hidden="true" />
          <div className="flex-1">
            <p className="text-sm font-medium text-rose-300">Không thể tải tin nhắn</p>
            <p className="text-xs text-neutral-300 mt-0.5">{error}</p>
          </div>
          <button
            onClick={refreshMessages}
            className="px-3 py-1.5 rounded-lg bg-rose-500/80 hover:bg-rose-500 text-white text-xs font-medium transition-colors"
          >
            Thử lại
          </button>
        </div>
      </LiquidCard>
    );
  };

  return (
    <div className="max-w-4xl mx-auto space-y-4 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-widest block">
            {isGuest ? 'Guest Chat' : 'Class Activity Feed'}
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight apple-text-headline">
            {isGuest ? 'Kênh Gửi Biên Lai & Thảo Luận' : 'Kênh Thảo Luận & Hoạt Động Lớp'}
          </h1>
          <p className="text-xs sm:text-sm text-neutral-400 mt-0.5">
            {isGuest 
              ? 'Gửi biên lai chuyển khoản, hỏi đáp và theo dõi trạng thái xử lý' 
              : 'Cập nhật biên lai nộp tiền và thông báo chính thức từ ban cán sự lớp 12A1'}
          </p>
        </div>
      </div>

      {renderGuestHeader()}
      {renderError()}

      {/* Message List */}
      <MessageList
        messages={messages}
        currentUserId={currentUser.id}
        isLoading={isLoading}
        onRecall={handleRecall}
        canRecall={canRecall}
        isRecalling={(id) => false} // Could track from hook if needed
        onViewReceipt={handleViewReceipt}
        pinnedMessage={pinnedMessage}
      />

      {/* Message Composer */}
      <LiquidCard variant="elevated" clarity="frosted" className="p-4 sm:p-6 border border-white/15 shadow-xl">
        <MessageComposer
          currentUser={currentUser}
          onSend={handleSend}
          isSending={false} // Could track from hook
          uploads={uploads}
          onAddUpload={addUpload}
          onRemoveUpload={removeUpload}
          onRetryUpload={retryUpload}
          disabled={false}
          placeholder={isGuest 
            ? 'Nhập nội dung hoặc đính kèm ảnh biên lai...' 
            : 'Gửi tin nhắn thảo luận...'}
        />
      </LiquidCard>

      {/* Guest-specific info footer */}
      {isGuest && (
        <LiquidCard variant="clear" clarity="clear" className="p-4 border border-neutral-700/50">
          <div className="flex items-start gap-3 text-xs">
            <Shield className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="space-y-1 text-neutral-300">
              <p className="font-medium text-white">Quy trình xử lý biên lai:</p>
              <ol className="space-y-1 pl-4 list-decimal text-neutral-400">
                <li>Gửi ảnh → Hệ thống tạo mã tham chiếu & mã thu hồi</li>
                <li>AI đọc mã GD, số tiền, ngân hàng, thời gian</li>
                <li>Kiểm tra trùng lặp với sổ cái (SHA-256 fingerprint)</li>
                <li>Xác thực → Ghi sổ quỹ & cập nhật trạng thái học sinh</li>
              </ol>
              <p className="mt-2 text-[10px] text-neutral-500">
                Mã thu hồi chỉ hiển thị 1 lần khi gửi. Hãy lưu lại nếu muốn thu hồi sau này.
              </p>
            </div>
          </div>
        </LiquidCard>
      )}

      {renderConnectionStatus()}
    </div>
  );
};

// Export for route integration
export default GuestChatPage;