import React, { useState, useEffect, useRef } from 'react';
import { 
  HelpCircle, 
  Sparkles, 
  Bug, 
  Check, 
  X, 
  Send, 
  Mail, 
  Copy, 
  ChevronRight,
  ShieldCheck,
  RefreshCw
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { LiquidGlassCard } from './LiquidGlassCard';

interface ContextMenuPosition {
  x: number;
  y: number;
}

export const FrostedContextMenu: React.FC = () => {
  const { addToast, setIsE2EModalOpen } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [pos, setPos] = useState<ContextMenuPosition>({ x: 0, y: 0 });
  const [isGliding, setIsGliding] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [reportText, setReportText] = useState('');
  const [reportSender, setReportSender] = useState('');
  const [copiedEmail, setCopiedEmail] = useState(false);

  const menuRef = useRef<HTMLDivElement>(null);
  const glideTimerRef = useRef<NodeJS.Timeout | null>(null);

  const RECIPIENT_EMAIL = 'dha5678675@gmail.com';
  const MENU_WIDTH = 256;
  const MENU_HEIGHT = 160;

  // Clamped position ensures menu is ALWAYS 100% inside web viewport
  const getClampedPos = (clientX: number, clientY: number): ContextMenuPosition => {
    const padding = 16;
    const maxX = window.innerWidth - MENU_WIDTH - padding;
    const maxY = window.innerHeight - MENU_HEIGHT - padding;

    const clampedX = Math.max(padding, Math.min(clientX, maxX));
    const clampedY = Math.max(padding, Math.min(clientY, maxY));

    return { x: clampedX, y: clampedY };
  };

  useEffect(() => {
    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault(); // Prevent native browser context menu

      const newPos = getClampedPos(e.clientX, e.clientY);

      if (isOpen) {
        // Continuous, silky-smooth spring motion to the new cursor position:
        // Gently compress slightly (scale: 0.94) and glide with Apple spring curve
        if (glideTimerRef.current) clearTimeout(glideTimerRef.current);
        setIsGliding(true);
        setPos(newPos);

        glideTimerRef.current = setTimeout(() => {
          setIsGliding(false);
        }, 280);
      } else {
        setPos(newPos);
        setIsGliding(false);
        setIsOpen(true);
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setIsGliding(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        setIsGliding(false);
        setIsHelpModalOpen(false);
      }
    };

    window.addEventListener('contextmenu', handleContextMenu);
    window.addEventListener('click', handleClickOutside);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('contextmenu', handleContextMenu);
      window.removeEventListener('click', handleClickOutside);
      window.removeEventListener('keydown', handleKeyDown);
      if (glideTimerRef.current) clearTimeout(glideTimerRef.current);
    };
  }, [isOpen]);

  const handleOpenHelp = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsHelpModalOpen(true);
    setIsOpen(false);
  };

  const handleOpenE2E = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsE2EModalOpen(true);
    setIsOpen(false);
  };

  const handleRefreshData = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(false);
    addToast({
      type: 'success',
      title: 'Đã đồng bộ dữ liệu sổ quỹ',
      description: 'Số dư và các giao dịch đã cập nhật mới nhất từ hệ thống.',
    });
  };

  const copyEmailToClipboard = () => {
    navigator.clipboard.writeText(RECIPIENT_EMAIL);
    setCopiedEmail(true);
    addToast({
      type: 'success',
      title: 'Đã sao chép email hỗ trợ',
      description: RECIPIENT_EMAIL,
    });
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  const handleSendReport = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportText.trim()) return;

    const subject = encodeURIComponent(`[ClassFund Báo Lỗi] từ ${reportSender || 'Học sinh'}`);
    const body = encodeURIComponent(
      `Chào Hải,\n\nTôi gửi thông tin báo lỗi / trợ giúp như sau:\n\nNgười gửi: ${reportSender || 'Học sinh/Phụ huynh'}\nNội dung: ${reportText}\nThời gian: ${new Date().toLocaleString('vi-VN')}\n\nTrân trọng!`
    );

    window.location.href = `mailto:${RECIPIENT_EMAIL}?subject=${subject}&body=${body}`;

    addToast({
      type: 'success',
      title: 'Đã mở email gửi tới dha5678675@gmail.com',
      description: 'Cảm ơn bạn! Đã chuẩn bị sẵn thư gửi trực tiếp tới Hải.',
    });

    setReportText('');
    setReportSender('');
    setIsHelpModalOpen(false);
  };

  return (
    <>
      {/* Butter-Smooth Frosted Liquid Glass Context Menu */}
      {isOpen && (
        <div
          ref={menuRef}
          className={`fixed z-50 select-none shadow-[0_25px_60px_rgba(0,0,0,0.65)] rounded-3xl w-64 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
            isGliding ? 'scale-95 opacity-90' : 'scale-100 opacity-100 animate-apple-fade-scale'
          }`}
          style={{
            left: `${pos.x}px`,
            top: `${pos.y}px`,
            transformOrigin: 'top left',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <LiquidGlassCard
            variant="modal"
            clarity="frosted"
            className="p-2.5 rounded-3xl w-full"
          >
            <div className="space-y-1">
              {/* Header Title */}
              <div className="px-3 py-1.5 border-b border-white/[0.08] flex items-center justify-between">
                <span className="text-[10px] font-bold text-sky-200 uppercase tracking-widest">Menu Tiện Ích</span>
                <span className="text-[9px] font-mono text-sky-400 px-1.5 py-0.5 rounded-full bg-sky-500/15 border border-sky-400/25">Liquid Glass</span>
              </div>

              {/* Item 1: Trợ giúp & Báo lỗi (gửi mail về dha5678675@gmail.com) */}
              <button
                onClick={handleOpenHelp}
                className="w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between gap-2.5 hover:bg-white/[0.12] text-white transition-all group active:scale-95"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-6 h-6 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center justify-center">
                    <HelpCircle className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="font-bold text-white group-hover:text-amber-300 transition-colors">
                      Trợ giúp & Báo lỗi
                    </p>
                    <p className="text-[10px] text-slate-200">Gửi mail tới {RECIPIENT_EMAIL}</p>
                  </div>
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-neutral-300 group-hover:text-white" />
              </button>

              {/* Item 2: Kiểm thử tự động E2E */}
              <button
                onClick={handleOpenE2E}
                className="w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between gap-2.5 hover:bg-white/[0.12] text-white transition-all group active:scale-95"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-6 h-6 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-500/30 flex items-center justify-center">
                    <ShieldCheck className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="font-bold text-white group-hover:text-sky-300 transition-colors">
                      Kiểm thử E2E (7 Test)
                    </p>
                    <p className="text-[10px] text-slate-200">Chạy kịch bản nộp quỹ & chống trùng</p>
                  </div>
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-neutral-300 group-hover:text-white" />
              </button>

              {/* Item 3: Làm mới dữ liệu sổ quỹ */}
              <button
                onClick={handleRefreshData}
                className="w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between gap-2.5 hover:bg-white/[0.12] text-white transition-all group active:scale-95"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center justify-center">
                    <RefreshCw className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="font-bold text-white group-hover:text-emerald-300 transition-colors">
                      Đồng bộ số dư
                    </p>
                    <p className="text-[10px] text-slate-200">Cập nhật giao dịch thời gian thực</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-emerald-300 font-bold px-1.5 py-0.5 rounded bg-emerald-500/10">Sync</span>
              </button>
            </div>
          </LiquidGlassCard>
        </div>
      )}

      {/* Help & Bug Report Frosted Modal targeting dha5678675@gmail.com */}
      {isHelpModalOpen && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xl animate-in fade-in duration-200"
          onClick={() => setIsHelpModalOpen(false)}
        >
          <div 
            className="w-full max-w-md rounded-3xl overflow-hidden animate-apple-fade-scale shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <LiquidGlassCard
              variant="modal"
              clarity="frosted"
              className="p-6 sm:p-8 space-y-5 rounded-3xl"
            >
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 text-xs font-bold text-amber-300 uppercase tracking-widest">
                  <Bug className="w-4 h-4" />
                  <span>Trung Tâm Hỗ Trợ & Báo Lỗi</span>
                </div>
                <h3 className="text-xl font-bold text-white tracking-tight mt-1 apple-text-headline">
                  Gửi Phản Hồi Cho Hải
                </h3>
              </div>
              <button
                onClick={() => setIsHelpModalOpen(false)}
                className="p-1.5 rounded-full text-neutral-300 hover:text-white bg-white/[0.08] hover:bg-white/[0.15] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Email Target Box */}
            <div className="p-3.5 rounded-2xl bg-white/[0.06] border border-white/10 flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-full bg-sky-500/20 border border-sky-400/30 flex items-center justify-center text-sky-300 shrink-0">
                  <Mail className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] text-sky-200 uppercase tracking-wider block font-semibold">Địa chỉ tiếp nhận Gmail</span>
                  <span className="font-mono text-white font-bold text-xs truncate block">{RECIPIENT_EMAIL}</span>
                </div>
              </div>

              <button
                onClick={copyEmailToClipboard}
                className="px-2.5 py-1.5 rounded-xl apple-btn-secondary text-[11px] font-semibold flex items-center gap-1 shrink-0"
              >
                {copiedEmail ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedEmail ? 'Đã chép' : 'Sao chép'}</span>
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSendReport} className="space-y-3.5 text-xs">
              <div className="space-y-1">
                <label className="font-bold text-slate-100">Tên của bạn hoặc học sinh liên hệ *</label>
                <input
                  type="text"
                  value={reportSender}
                  onChange={(e) => setReportSender(e.target.value)}
                  placeholder="VD: Nguyễn Văn A, hoặc phụ huynh..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white/[0.06] border border-white/15 text-white placeholder-neutral-400 focus:outline-none focus:border-sky-400 transition-colors font-medium"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-100">Nội dung thắc mắc / Báo lỗi gửi đến Hải *</label>
                <textarea
                  value={reportText}
                  onChange={(e) => setReportText(e.target.value)}
                  rows={3}
                  placeholder="Mô tả chi tiết thắc mắc, lỗi tính năng, sai số tiền hoặc góp ý giao diện..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white/[0.06] border border-white/15 text-white placeholder-neutral-400 focus:outline-none focus:border-sky-400 transition-colors font-medium"
                  required
                />
              </div>

              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsHelpModalOpen(false)}
                  className="flex-1 py-2.5 rounded-full apple-btn-secondary text-white font-semibold"
                >
                  Đóng
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 rounded-full apple-btn-primary font-bold flex items-center justify-center gap-1.5 shadow-lg shadow-sky-600/30"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Gửi tới {RECIPIENT_EMAIL}</span>
                </button>
              </div>
            </form>
            </LiquidGlassCard>
          </div>
        </div>
      )}
    </>
  );
};
