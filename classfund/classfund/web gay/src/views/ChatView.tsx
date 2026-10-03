import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND } from '../data/mockDatabase';
import { ChatMessage } from '../types';
import { 
  Send, 
  Image as ImageIcon, 
  Pin, 
  CheckCircle2, 
  Flame
} from 'lucide-react';

export const ChatView: React.FC = () => {
  const { chatMessages, sendChatMessage, currentUser, setSelectedTransaction, ledgerEntries, setCurrentTab } = useApp();
  const [inputText, setInputText] = useState('');
  const [isModAnnouncement, setIsModAnnouncement] = useState(false);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    sendChatMessage(
      inputText, 
      isModAnnouncement ? 'ANNOUNCEMENT' : 'TEXT',
      isModAnnouncement
    );
    setInputText('');
    setIsModAnnouncement(false);
  };

  const pinnedMessage = chatMessages.find((m) => m.is_pinned);

  return (
    <div className="max-w-4xl mx-auto space-y-4 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-widest block">
            Class Activity Feed
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight apple-text-headline">
            Kênh Thảo Luận & Hoạt Động Lớp.
          </h1>
          <p className="text-xs sm:text-sm text-neutral-400 mt-0.5">
            Cập nhật biên lai nộp tiền và thông báo chính thức từ ban cán sự lớp 12A1.
          </p>
        </div>
      </div>

      {/* Pinned Moderator Card with Frosted Mod Liquid Glass */}
      {pinnedMessage && (
        <LiquidCard variant="mod" clarity="frosted" className="rounded-2xl p-4 sm:p-5 shadow-xl border border-amber-500/30">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-300 shrink-0">
              <Pin className="w-4 h-4 fill-amber-300/40" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">Thông báo ghim từ Moderator</span>
                <span aria-hidden="true" className="text-neutral-500">·</span>
                <span className="text-xs text-white font-medium">{pinnedMessage.sender_name}</span>
                <span className="text-[10px] text-neutral-400 font-mono">{pinnedMessage.created_at}</span>
              </div>
              <p className="text-xs sm:text-sm text-neutral-100 font-medium mt-1 leading-relaxed">
                {pinnedMessage.content}
              </p>
            </div>
          </div>
        </LiquidCard>
      )}

      {/* Chat Messages Feed Container */}
      <LiquidCard variant="default" clarity="balanced" className="p-4 sm:p-6 space-y-4 min-h-[480px] max-h-[620px] overflow-y-auto flex flex-col-reverse">
        {chatMessages.map((msg) => {
          const isCurrentUser = msg.sender_id === currentUser.id;
          const isModerator = msg.sender_role === 'MODERATOR' || msg.sender_role === 'TREASURER';

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isCurrentUser ? 'items-end' : 'items-start'} space-y-1`}
            >
              {/* Sender Name & Role Info */}
              <div className="flex items-center gap-2 px-2 text-[11px] text-neutral-400">
                <span className="font-semibold text-neutral-300">{msg.sender_name}</span>
                {isModerator && (
                  <span className="px-1.5 py-0.2 rounded-full bg-amber-500/15 text-amber-300 font-bold text-[10px] border border-amber-500/25">
                    MOD
                  </span>
                )}
                <span className="text-neutral-500">{msg.created_at}</span>
              </div>

              {/* Message Bubble Body */}
              {msg.message_type === 'RECEIPT' && msg.receipt_data ? (
                /* Phase 8: Receipt Message Card with Photo Preview */
                <div 
                  className={`max-w-md rounded-2xl p-4 sm:p-5 apple-card-elevated border border-white/15 shadow-xl space-y-3 cursor-pointer hover:border-sky-400/40 transition-all ${
                    isCurrentUser ? 'bg-sky-950/20' : ''
                  }`}
                  onClick={() => {
                    const matchedEntry = ledgerEntries.find(e => e.id === msg.receipt_data?.entry_id);
                    if (matchedEntry) setSelectedTransaction(matchedEntry);
                  }}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-emerald-400 font-medium inline-flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{msg.receipt_data.status === 'VERIFIED' ? 'Đã xác minh AI' : 'Biên lai chuyển khoản'}</span>
                    </span>
                    <span className="text-neutral-400 font-mono text-[11px]">{msg.receipt_data.time}</span>
                  </div>

                  {/* Embedded Receipt Image */}
                  <div className="relative rounded-xl overflow-hidden border border-white/10 aspect-[16/10] bg-black">
                    <img
                      src={msg.receipt_data.image_url}
                      alt="Biên lai"
                      referrerPolicy="no-referrer"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent flex items-end p-3 justify-between">
                      <div>
                        <p className="text-[10px] text-neutral-400">Số tiền chuyển:</p>
                        <p className="text-lg font-extrabold text-emerald-400 font-tabular">
                          +{formatVND(msg.receipt_data.amount)}
                        </p>
                      </div>
                      <span className="px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md text-white text-[10px] font-mono border border-white/20">
                        {msg.receipt_data.transaction_code}
                      </span>
                    </div>
                  </div>

                  {msg.content && (
                    <p className="text-xs text-neutral-200 leading-relaxed">{msg.content}</p>
                  )}

                  <div className="pt-1 flex items-center justify-between text-[11px] text-sky-400">
                    <span>Người gửi: {msg.receipt_data.sender_name}</span>
                    <span className="inline-flex items-center gap-0.5 font-medium">Chi tiết →</span>
                  </div>
                </div>
              ) : msg.message_type === 'ANNOUNCEMENT' ? (
                /* Phase 9: Moderator Announcement Bubble */
                <div className="apple-mod-card max-w-lg rounded-2xl p-4 text-white shadow-lg space-y-1">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-amber-300">
                    <Flame className="w-3.5 h-3.5" />
                    <span>THÔNG BÁO TỪ BAN CÁN SỰ LỚP</span>
                  </div>
                  <p className="text-xs sm:text-sm text-neutral-100 leading-relaxed font-medium">
                    {msg.content}
                  </p>
                </div>
              ) : (
                /* Standard iOS / Apple Frosted Bubble */
                <div
                  className={`max-w-md rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed shadow-sm ${
                    isCurrentUser
                      ? 'bg-sky-600 text-white rounded-br-sm'
                      : 'apple-frosted-glass text-neutral-100 rounded-bl-sm border border-white/10'
                  }`}
                >
                  {msg.content}
                </div>
              )}
            </div>
          );
        })}
      </LiquidCard>

      {/* Input Box Bar (Apple Frosted Pill) */}
      <form onSubmit={handleSend} className="space-y-2">
        {(currentUser.role === 'MODERATOR' || currentUser.role === 'TREASURER') && (
          <div className="flex items-center gap-2 px-2">
            <label className="flex items-center gap-1.5 text-xs text-amber-300 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isModAnnouncement}
                onChange={(e) => setIsModAnnouncement(e.target.checked)}
                className="rounded border-amber-400 text-amber-500 focus:ring-0"
              />
              <span className="font-semibold">Đăng dưới dạng Thông báo Moderator [MOD]</span>
            </label>
          </div>
        )}

        <div className="flex items-center gap-2 p-1.5 rounded-full bg-neutral-900/80 backdrop-blur-2xl border border-white/15 shadow-2xl">
          <button
            type="button"
            onClick={() => setCurrentTab('upload')}
            className="w-9 h-9 rounded-full bg-white/[0.06] hover:bg-white/[0.12] flex items-center justify-center text-sky-400 hover:text-white transition-all active:scale-95"
            title="Đính kèm ảnh biên lai"
          >
            <ImageIcon className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={
              isModAnnouncement 
                ? 'Nhập nội dung thông báo nổi bật...' 
                : 'Gửi tin nhắn thảo luận...'
            }
            className="flex-1 bg-transparent px-3 py-2 text-xs sm:text-sm text-white placeholder-neutral-500 focus:outline-none"
          />

          <button
            type="submit"
            disabled={!inputText.trim()}
            className="min-h-[36px] px-4 rounded-full apple-btn-primary font-medium text-xs flex items-center gap-1.5 shadow-md active:scale-95 transition-all disabled:opacity-40"
          >
            <span>Gửi</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
    </div>
  );
};
