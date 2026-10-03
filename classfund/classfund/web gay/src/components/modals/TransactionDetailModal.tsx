import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { formatVND } from '../../data/mockDatabase';
import { LiquidGlassCard } from '../common/LiquidGlassCard';
import { 
  X, 
  RotateCcw, 
  AlertTriangle
} from 'lucide-react';

export const TransactionDetailModal: React.FC = () => {
  const { 
    selectedTransaction, 
    setSelectedTransaction, 
    currentUser, 
    revertTransaction 
  } = useApp();

  const [isConfirmingRevert, setIsConfirmingRevert] = useState(false);
  const [revertReason, setRevertReason] = useState('');

  if (!selectedTransaction) return null;

  const isReverted = selectedTransaction.status === 'REVERTED';
  const isReversalEntry = selectedTransaction.type === 'REVERT';
  const canRevert = (currentUser.role === 'TREASURER' || currentUser.role === 'MODERATOR') && 
                    !isReverted && 
                    !isReversalEntry && 
                    selectedTransaction.status === 'VERIFIED';

  const handleExecuteRevert = () => {
    if (!revertReason.trim()) return;
    const success = revertTransaction(selectedTransaction.id, revertReason);
    if (success) {
      setIsConfirmingRevert(false);
      setSelectedTransaction(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xl animate-in fade-in duration-200">
      {/* Outer rounded card with overflow-hidden ensures scrollbar NEVER overflows outside corners */}
      <div 
        className="w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden animate-apple-fade-scale flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <LiquidGlassCard
          variant="modal"
          clarity="frosted"
          className="w-full h-full p-0 rounded-3xl flex flex-col"
        >
        {/* Inner scrollable viewport with inset scrollbar */}
        <div className="p-6 sm:p-8 space-y-6 overflow-y-auto apple-scrollbar pr-5 mr-1 my-1">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold uppercase tracking-widest ${
                  isReverted ? 'text-amber-400' : selectedTransaction.type === 'CREDIT' ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                  {isReverted ? 'Giao dịch đã thu hồi' : selectedTransaction.type === 'CREDIT' ? 'Bút toán Nạp' : 'Bút toán Chi'}
                </span>
                <span aria-hidden="true" className="text-white/40">·</span>
                <span className="text-xs text-sky-200 font-mono font-semibold">{selectedTransaction.transaction_code}</span>
              </div>
              <p className="text-2xl sm:text-3xl font-extrabold text-white mt-1 font-tabular apple-text-headline">
                {selectedTransaction.type === 'CREDIT' ? '+' : '-'}{formatVND(selectedTransaction.amount)}
              </p>
            </div>

            <button
              onClick={() => {
                setSelectedTransaction(null);
                setIsConfirmingRevert(false);
              }}
              className="p-1.5 rounded-full text-neutral-300 hover:text-white bg-white/[0.08] hover:bg-white/[0.16] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Reversal Chain Visual Warning if Reverted */}
          {isReverted && (
            <div className="p-4 rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-100 space-y-2 text-xs">
              <div className="flex items-center gap-2 font-bold">
                <RotateCcw className="w-4 h-4 text-amber-400" />
                <span>Chuỗi thu hồi (Revert Chain Trace):</span>
              </div>
              <div className="pl-2 border-l-2 border-amber-400/50 space-y-1 text-slate-100 font-medium">
                <p>1. Giao dịch gốc: <span className="font-mono text-white font-bold">{selectedTransaction.transaction_code}</span> ({selectedTransaction.created_at})</p>
                <p>2. Người thu hồi: <span className="font-bold text-white">{selectedTransaction.reverted_by}</span> ({selectedTransaction.reverted_at})</p>
                <p>3. Lý do thu hồi: <span className="italic text-amber-200">{selectedTransaction.revert_reason}</span></p>
                <p>4. Bút toán đảo: <span className="font-mono text-amber-300 font-bold">{selectedTransaction.reversal_entry_id}</span></p>
              </div>
            </div>
          )}

          {/* Receipt Image Preview if present */}
          {selectedTransaction.image_url && (
            <div className="space-y-1.5">
              <p className="text-xs font-bold text-white uppercase tracking-widest">Ảnh biên lai gốc</p>
              <div className="rounded-2xl overflow-hidden border border-white/15 aspect-[16/9] bg-black shadow-inner">
                <img
                  src={selectedTransaction.image_url}
                  alt="Biên lai gốc"
                  referrerPolicy="no-referrer"
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          )}

          {/* Detailed Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3.5 rounded-2xl bg-white/[0.06] border border-white/10 space-y-1">
              <span className="text-sky-200 text-[11px] block font-medium">Người gửi / Đối tượng</span>
              <span className="font-bold text-white block truncate text-sm">{selectedTransaction.sender_name}</span>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.06] border border-white/10 space-y-1">
              <span className="text-sky-200 text-[11px] block font-medium">Người tải ảnh lên</span>
              <span className="font-bold text-white block truncate text-sm">{selectedTransaction.uploaded_by}</span>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.06] border border-white/10 space-y-1">
              <span className="text-sky-200 text-[11px] block font-medium">Thời gian ghi nhận</span>
              <span className="font-bold text-white font-tabular block">{selectedTransaction.created_at}</span>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.06] border border-white/10 space-y-1">
              <span className="text-sky-200 text-[11px] block font-medium">Độ tin cậy AI</span>
              <span className="font-extrabold text-sky-400 font-mono block text-sm">
                {selectedTransaction.ai_confidence ? `${selectedTransaction.ai_confidence}%` : 'N/A (Thủ công)'}
              </span>
            </div>
          </div>

          {selectedTransaction.note && (
            <div className="p-3.5 rounded-2xl bg-white/[0.06] border border-white/10 space-y-1 text-xs">
              <span className="text-sky-200 text-[11px] block font-semibold">Ghi chú giao dịch:</span>
              <p className="text-white leading-relaxed font-medium">{selectedTransaction.note}</p>
            </div>
          )}

          {/* Revert Action Zone */}
          {canRevert && (
            <div className="pt-2 border-t border-white/[0.08] space-y-3">
              {!isConfirmingRevert ? (
                <button
                  onClick={() => setIsConfirmingRevert(true)}
                  className="w-full min-h-[44px] rounded-full bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 font-bold text-xs flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Thu hồi giao dịch này (Revert)</span>
                </button>
              ) : (
                <div className="p-4 rounded-2xl bg-rose-500/15 border border-rose-500/35 space-y-3 animate-apple-fade-scale">
                  <div className="flex items-center gap-2 text-rose-300 text-xs font-bold">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Xác nhận thu hồi giao dịch?</span>
                  </div>
                  <p className="text-xs text-slate-100 leading-relaxed font-medium">
                    Hệ thống sẽ giữ nguyên vết lịch sử, đánh dấu <span className="font-mono text-rose-300 font-bold">REVERTED</span> và tự động sinh bút toán đảo để hoàn nguyên số dư quỹ.
                  </p>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-white">Lý do thu hồi (Bắt buộc) *</label>
                    <input
                      type="text"
                      value={revertReason}
                      onChange={(e) => setRevertReason(e.target.value)}
                      placeholder="VD: Chuyển nhầm số tiền, đã hoàn tiền mặt..."
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/60 border border-white/15 text-white text-xs focus:outline-none focus:border-rose-400 font-medium"
                      autoFocus
                    />
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <button
                      onClick={() => setIsConfirmingRevert(false)}
                      className="flex-1 py-2 rounded-full apple-btn-secondary text-xs font-semibold text-white"
                    >
                      Hủy bỏ
                    </button>
                    <button
                      onClick={handleExecuteRevert}
                      disabled={!revertReason.trim()}
                      className="flex-1 py-2 rounded-full bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white font-bold text-xs shadow-md transition-all"
                    >
                      Xác nhận Revert
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        </LiquidGlassCard>
      </div>
    </div>
  );
};
