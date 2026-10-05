import React, { useState } from 'react';
import { RotateCcw, X, AlertTriangle, Loader2, CheckCircle2 } from 'lucide-react';
import { MessageStatus } from '../../types/chat';
import { LiquidCard } from '../../components/common/LiquidCard';
import { useRecall } from '../../hooks/useRecall';
import { RecallEligibility } from '../../lib/recall';

interface RecallButtonProps {
  messageId: string;
  status: MessageStatus;
  canRecall: boolean;
  onRecall: (messageId: string, status: MessageStatus, reason?: string) => void;
  isRecalling?: boolean;
  className?: string;
}

export const RecallButton: React.FC<RecallButtonProps> = ({
  messageId,
  status,
  canRecall,
  onRecall,
  isRecalling = false,
  className = '',
}) => {
  const [showConfirm, setShowConfirm] = useState(false);
  const [customReason, setCustomReason] = useState('');
  const [eligibility, setEligibility] = useState<RecallEligibility | null>(null);
  const [checkingEligibility, setCheckingEligibility] = useState(false);

  const { checkEligibility } = useRecall();

  if (!canRecall) return null;

  const handleCheckEligibility = async () => {
    setCheckingEligibility(true);
    try {
      const result = await checkEligibility(messageId);
      setEligibility(result);
      if (result.eligible) {
        setShowConfirm(true);
      } else {
        // Show error toast or handle ineligibility
        console.warn('[RecallButton] Not eligible:', result.reason);
      }
    } catch (error) {
      console.error('[RecallButton] Eligibility check failed:', error);
    } finally {
      setCheckingEligibility(false);
    }
  };

  const handleConfirm = () => {
    onRecall(messageId, status, customReason || undefined);
    setShowConfirm(false);
    setCustomReason('');
  };

  const getRecallLabel = (status: MessageStatus) => {
    switch (status) {
      case 'pending':
      case 'processing':
      case 'awaiting_review':
        return 'Thu hồi yêu cầu';
      case 'posted':
        return 'Yêu cầu đảo bút toán';
      default:
        return 'Thu hồi';
    }
  };

  const getRecallDescription = (status: MessageStatus) => {
    switch (status) {
      case 'pending':
      case 'processing':
      case 'awaiting_review':
        return 'Hủy bỏ tin nhắn này trước khi hệ thống xử lý. Tin nhắn sẽ bị xóa và không thể khôi phục.';
      case 'posted':
        return 'Tạo bút toán đảo để hoàn trả số tiền đã ghi sổ. Hành động này không thể undo.';
      default:
        return 'Thu hồi tin nhắn này.';
    }
  };

  return (
    <>
      <button
        onClick={handleCheckEligibility}
        disabled={isRecalling || checkingEligibility}
        className={`
          inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full 
          bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 
          text-rose-300 text-xs font-medium transition-all
          disabled:opacity-50 disabled:cursor-not-allowed
          ${className}
        `}
        aria-label={getRecallLabel(status)}
        title={getRecallLabel(status)}
      >
        <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
        <span>{isRecalling ? 'Đang thu hồi...' : checkingEligibility ? 'Kiểm tra...' : 'THU HỘI'}</span>
      </button>

      {/* Confirmation Modal */}
      {showConfirm && eligibility?.eligible && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="recall-modal-title"
          aria-describedby="recall-modal-description"
        >
          <div className="w-full max-w-md">
            <LiquidCard variant="elevated" clarity="frosted" className="p-6 animate-in zoom-in-95">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-5 h-5 text-rose-400" aria-hidden="true" />
                </div>
                <div className="flex-1">
                  <h3 id="recall-modal-title" className="text-lg font-bold text-white">
                    Xác nhận {getRecallLabel(status).toLowerCase()}
                  </h3>
                  <p id="recall-modal-description" className="text-sm text-neutral-300 mt-1">
                    {getRecallDescription(status)}
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <textarea
                  value={customReason}
                  onChange={(e) => setCustomReason(e.target.value)}
                  placeholder="Lý do thu hồi (tùy chọn)"
                  rows={3}
                  className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/10 text-white text-sm focus:outline-none focus:border-sky-400 transition-colors resize-none"
                  aria-label="Lý do thu hồi"
                />

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={() => { setShowConfirm(false); setCustomReason(''); }}
                    disabled={isRecalling}
                    className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-neutral-300 text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    Hủy
                  </button>
                  <button
                    onClick={handleConfirm}
                    disabled={isRecalling}
                    className="px-4 py-2 rounded-xl bg-rose-500/80 hover:bg-rose-500 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {isRecalling ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                        <span>Đang xử lý...</span>
                      </>
                    ) : (
                      <>
                        <RotateCcw className="w-4 h-4" aria-hidden="true" />
                        <span>Xác nhận thu hồi</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </LiquidCard>
          </div>
        </div>
      )}

      {/* Ineligibility Modal */}
      {showConfirm && eligibility && !eligibility.eligible && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="recall-ineligible-title"
        >
          <div className="w-full max-w-md">
            <LiquidCard variant="elevated" clarity="frosted" className="p-6 animate-in zoom-in-95">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-5 h-5 text-amber-400" aria-hidden="true" />
                </div>
                <div className="flex-1">
                  <h3 id="recall-ineligible-title" className="text-lg font-bold text-white">
                    Không thể thu hồi
                  </h3>
                  <p className="text-sm text-neutral-300 mt-1">
                    {eligibility.reason || 'Tin nhắn này không đủ điều kiện để thu hồi.'}
                  </p>
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => { setShowConfirm(false); setCustomReason(''); }}
                  className="px-4 py-2 rounded-xl bg-amber-500/80 hover:bg-amber-500 text-white text-sm font-medium transition-colors"
                >
                  Đóng
                </button>
              </div>
            </LiquidCard>
          </div>
        </div>
      )}
    </>
  );
};

// Simpler recall trigger for inline use (e.g., in message context menu)
export const RecallTrigger: React.FC<{
  messageId: string;
  status: MessageStatus;
  canRecall: boolean;
  onRecall: (messageId: string, reason?: string) => void;
  isRecalling?: boolean;
}> = ({ messageId, status, canRecall, onRecall, isRecalling }) => {
  if (!canRecall) return null;

  return (
    <button
      onClick={() => onRecall(messageId)}
      disabled={isRecalling}
      className="flex items-center gap-2 px-3 py-2 text-rose-300 hover:bg-rose-500/10 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
      role="menuitem"
    >
      <RotateCcw className="w-4 h-4" aria-hidden="true" />
      <span>Thu hồi</span>
    </button>
  );
};