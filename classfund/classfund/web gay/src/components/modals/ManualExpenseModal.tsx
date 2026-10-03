import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { formatVND } from '../../data/mockDatabase';
import { LiquidGlassCard } from '../common/LiquidGlassCard';
import { X, MinusCircle } from 'lucide-react';

export const ManualExpenseModal: React.FC = () => {
  const { isExpenseModalOpen, setIsExpenseModalOpen, addManualExpense, balances } = useApp();
  
  const [amount, setAmount] = useState<number>(100000);
  const [recipient, setRecipient] = useState<string>('');
  const [reason, setReason] = useState<string>('');

  if (!isExpenseModalOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (amount <= 0 || !recipient.trim() || !reason.trim()) return;

    addManualExpense(amount, recipient.trim(), reason.trim());
    setIsExpenseModalOpen(false);
    setAmount(100000);
    setRecipient('');
    setReason('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xl animate-in fade-in duration-200">
      <div 
        className="w-full max-w-md rounded-3xl shadow-2xl overflow-hidden animate-apple-fade-scale"
        onClick={(e) => e.stopPropagation()}
      >
        <LiquidGlassCard
          variant="modal"
          clarity="frosted"
          className="p-6 sm:p-8 space-y-6 rounded-3xl"
        >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-rose-400 font-bold">
            <MinusCircle className="w-5 h-5" />
            <h3 className="text-lg text-white apple-text-headline">Ghi Sổ Chi Tiền Quỹ</h3>
          </div>
          <button
            onClick={() => setIsExpenseModalOpen(false)}
            className="p-1.5 rounded-full text-neutral-400 hover:text-white bg-white/[0.06] hover:bg-white/[0.12] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="space-y-1">
            <label className="font-semibold text-neutral-300">Số tiền chi (VND) *</label>
            <input
              type="number"
              step="10000"
              min="1000"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white font-mono text-sm focus:outline-none focus:border-rose-400"
              required
            />
            <p className="text-[11px] text-neutral-400">Số dư hiện tại: {formatVND(balances.currentBalance)}</p>
          </div>

          <div className="space-y-1">
            <label className="font-semibold text-neutral-300">Người / Đơn vị nhận tiền *</label>
            <input
              type="text"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder="VD: Cửa hàng in Photo, Cửa hàng hoa..."
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white text-xs sm:text-sm focus:outline-none focus:border-rose-400"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="font-semibold text-neutral-300">Nội dung / Mục đích chi *</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="VD: Chi mua 35 bộ đề cương ôn tập giữa kì..."
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white text-xs sm:text-sm focus:outline-none focus:border-rose-400"
              required
            />
          </div>

          <div className="pt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsExpenseModalOpen(false)}
              className="flex-1 py-2.5 rounded-full apple-btn-secondary text-neutral-300 font-medium"
            >
              Hủy
            </button>
            <button
              type="submit"
              className="flex-1 py-2.5 rounded-full bg-rose-600 hover:bg-rose-500 text-white font-bold shadow-lg shadow-rose-600/30"
            >
              Xác nhận Ghi sổ
            </button>
          </div>
        </form>
        </LiquidGlassCard>
      </div>
    </div>
  );
};
