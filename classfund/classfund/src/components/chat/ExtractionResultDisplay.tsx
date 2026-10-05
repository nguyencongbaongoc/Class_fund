import React from 'react';
import { Shield, AlertTriangle, CheckCircle2, XCircle, Loader2, RotateCcw } from 'lucide-react';
import { LiquidCard } from '../common/LiquidCard';
import { MessageStatus } from '../../types/chat';

interface ExtractionResultDisplayProps {
  extraction?: {
    transaction_code?: string;
    amount?: number;
    sender_name?: string;
    bank_name?: string;
    transaction_time?: string;
    confidence?: number;
    status?: string;
  };
  fieldConfidences?: Record<string, number>;
  messageStatus: MessageStatus;
  isOwn: boolean;
}

const formatVND = (amount: number) => {
  return new Intl.NumberFormat('vi-VN').format(amount);
};

const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return 'emerald';
  if (confidence >= 0.6) return 'amber';
  return 'rose';
};

const getConfidenceLabel = (confidence: number) => {
  if (confidence >= 0.8) return 'Cao';
  if (confidence >= 0.6) return 'Trung bình';
  return 'Thấp';
};

const ConfidenceBar: React.FC<{ confidence: number; label: string }> = ({ confidence, label }) => {
  const color = getConfidenceColor(confidence);
  const colorClasses = {
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    rose: 'bg-rose-500',
  };
  
  return (
    <div className="flex items-center gap-2 text-[10px]">
      <span className="w-20 text-neutral-300">{label}</span>
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div 
          className={`h-full ${colorClasses[color]} transition-all duration-300`}
          style={{ width: `${confidence * 100}%` }}
        />
      </div>
      <span className={`w-14 text-right font-mono ${color === 'emerald' ? 'text-emerald-400' : color === 'amber' ? 'text-amber-400' : 'text-rose-400'}`}>
        {Math.round(confidence * 100)}%
      </span>
    </div>
  );
};

export const ExtractionResultDisplay: React.FC<ExtractionResultDisplayProps> = ({
  extraction,
  fieldConfidences,
  messageStatus,
  isOwn,
}) => {
  if (!extraction) return null;

  const isProcessing = messageStatus === 'processing';
  const isAwaitingReview = messageStatus === 'awaiting_review';
  const isPosted = messageStatus === 'posted';
  const isRejected = messageStatus === 'rejected' || messageStatus === 'failed';
  const isRecalled = messageStatus === 'recalled';

  const overallConfidence = extraction.confidence || 0;
  const confidenceColor = getConfidenceColor(overallConfidence);

  // Status indicator
  const renderStatusBadge = () => {
    if (isProcessing) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30 text-[10px] font-medium">
          <Loader2 className="w-3 h-3 animate-spin" />
          Đang xử lý AI...
        </span>
      );
    }
    if (isAwaitingReview) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px] font-medium">
          <AlertTriangle className="w-3 h-3" />
          Cần kiểm tra thủ công
        </span>
      );
    }
    if (isPosted) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-medium">
          <CheckCircle2 className="w-3 h-3" />
          Đã ghi sổ
        </span>
      );
    }
    if (isRejected) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 text-[10px] font-medium">
          <XCircle className="w-3 h-3" />
          Từ chối / Lỗi
        </span>
      );
    }
    if (isRecalled) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-neutral-500/20 text-neutral-400 border border-neutral-500/30 text-[10px] font-medium">
          <RotateCcw className="w-3 h-3" />
          Đã thu hồi
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-neutral-500/20 text-neutral-400 border border-neutral-500/30 text-[10px] font-medium">
        <Shield className="w-3 h-3" />
        Đang chờ
      </span>
    );
  };

  return (
    <LiquidCard 
      variant={isOwn ? 'elevated' : 'default'} 
      clarity="frosted" 
      className={`p-4 space-y-3 ${isOwn ? 'bg-sky-950/30 border-sky-500/20' : 'border-white/10'}`}
    >
      {/* Header with status and confidence */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            {renderStatusBadge()}
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
              confidenceColor === 'emerald' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
              confidenceColor === 'amber' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
              'bg-rose-500/20 text-rose-400 border-rose-500/30'
            }`}>
              Độ tin cậy: {Math.round(overallConfidence * 100)}% ({getConfidenceLabel(overallConfidence)})
            </span>
          </div>
        </div>
      </div>

      {/* Extraction fields */}
      <div className="space-y-2">
        {extraction.transaction_code && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.03] border border-white/10">
            <span className="w-28 text-[11px] text-neutral-400 font-medium">Mã GD:</span>
            <span className="flex-1 font-mono text-xs text-white break-all">{extraction.transaction_code}</span>
            {fieldConfidences?.transaction_code !== undefined && (
              <span className={`text-[10px] font-mono ${getConfidenceColor(fieldConfidences.transaction_code) === 'emerald' ? 'text-emerald-400' : getConfidenceColor(fieldConfidences.transaction_code) === 'amber' ? 'text-amber-400' : 'text-rose-400'}`}>
                {Math.round((fieldConfidences.transaction_code || 0) * 100)}%
              </span>
            )}
          </div>
        )}
        
        {extraction.amount !== undefined && extraction.amount !== null && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.03] border border-white/10">
            <span className="w-28 text-[11px] text-neutral-400 font-medium">Số tiền:</span>
            <span className="flex-1 font-tabular text-sm font-bold text-emerald-400">+{formatVND(extraction.amount)} VND</span>
            {fieldConfidences?.amount !== undefined && (
              <span className={`text-[10px] font-mono ${getConfidenceColor(fieldConfidences.amount) === 'emerald' ? 'text-emerald-400' : getConfidenceColor(fieldConfidences.amount) === 'amber' ? 'text-amber-400' : 'text-rose-400'}`}>
                {Math.round((fieldConfidences.amount || 0) * 100)}%
              </span>
            )}
          </div>
        )}
        
        {extraction.sender_name && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.03] border border-white/10">
            <span className="w-28 text-[11px] text-neutral-400 font-medium">Người gửi:</span>
            <span className="flex-1 text-xs text-white">{extraction.sender_name}</span>
            {fieldConfidences?.sender_name !== undefined && (
              <span className={`text-[10px] font-mono ${getConfidenceColor(fieldConfidences.sender_name) === 'emerald' ? 'text-emerald-400' : getConfidenceColor(fieldConfidences.sender_name) === 'amber' ? 'text-amber-400' : 'text-rose-400'}`}>
                {Math.round((fieldConfidences.sender_name || 0) * 100)}%
              </span>
            )}
          </div>
        )}
        
        {extraction.bank_name && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.03] border border-white/10">
            <span className="w-28 text-[11px] text-neutral-400 font-medium">Ngân hàng:</span>
            <span className="flex-1 text-xs text-sky-400">{extraction.bank_name}</span>
            {fieldConfidences?.bank_name !== undefined && (
              <span className={`text-[10px] font-mono ${getConfidenceColor(fieldConfidences.bank_name) === 'emerald' ? 'text-emerald-400' : getConfidenceColor(fieldConfidences.bank_name) === 'amber' ? 'text-amber-400' : 'text-rose-400'}`}>
                {Math.round((fieldConfidences.bank_name || 0) * 100)}%
              </span>
            )}
          </div>
        )}
        
        {extraction.transaction_time && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.03] border border-white/10">
            <span className="w-28 text-[11px] text-neutral-400 font-medium">Thời gian:</span>
            <span className="flex-1 text-xs text-neutral-300 font-mono">{extraction.transaction_time}</span>
            {fieldConfidences?.transaction_time !== undefined && (
              <span className={`text-[10px] font-mono ${getConfidenceColor(fieldConfidences.transaction_time) === 'emerald' ? 'text-emerald-400' : getConfidenceColor(fieldConfidences.transaction_time) === 'amber' ? 'text-amber-400' : 'text-rose-400'}`}>
                {Math.round((fieldConfidences.transaction_time || 0) * 100)}%
              </span>
            )}
          </div>
        )}
      </div>

      {/* Field confidence breakdown */}
      {fieldConfidences && Object.keys(fieldConfidences).length > 0 && (
        <div className="pt-2 border-t border-white/10">
          <p className="text-[10px] text-neutral-500 mb-2 uppercase tracking-wider">Chi tiết độ tin cậy từng trường:</p>
          <div className="space-y-1">
            {Object.entries(fieldConfidences).map(([field, confidence]) => (
              <ConfidenceBar 
                key={field} 
                confidence={confidence} 
                label={field.replace('_', ' ').toUpperCase()} 
              />
            ))}
          </div>
        </div>
      )}

      {/* Warning for low confidence */}
      {isAwaitingReview && overallConfidence < 0.7 && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-[10px] text-amber-300">
              <p className="font-medium">Độ tin cậy thấp - Cần kiểm tra thủ công</p>
              <p className="mt-1">AI không đủ tự tin để tự động ghi sổ. Thủ quỹ cần xác thực thông tin trước khi duyệt.</p>
            </div>
          </div>
        </div>
      )}

      {/* Duplicate warning */}
      {extraction.status === 'DUPLICATE' && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30">
          <div className="flex items-start gap-2">
            <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-[10px] text-rose-300">
              <p className="font-medium">Phát hiện trùng lặp</p>
              <p className="mt-1">Biên lai này có mã giao dịch trùng với bản ghi đã tồn tại trong sổ cái.</p>
            </div>
          </div>
        </div>
      )}
    </LiquidCard>
  );
};