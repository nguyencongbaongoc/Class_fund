import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { formatVND } from '../../data/mockDatabase';
import { LiquidGlassCard } from '../common/LiquidGlassCard';
import { X, Users } from 'lucide-react';

export const CreateCampaignModal: React.FC = () => {
  const { isCreateCampaignModalOpen, setIsCreateCampaignModalOpen, addToast } = useApp();
  
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [expectedAmount, setExpectedAmount] = useState(50000);
  const [endDate, setEndDate] = useState('2026-10-31');

  if (!isCreateCampaignModalOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    addToast({
      type: 'success',
      title: 'Đã tạo đợt thu mới thành công!',
      description: `Đợt thu "${title}" (${formatVND(expectedAmount)}/học sinh) đã được kích hoạt.`
    });
    setIsCreateCampaignModalOpen(false);
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
          <div className="flex items-center gap-2 text-sky-400 font-bold">
            <Users className="w-5 h-5" />
            <h3 className="text-lg text-white apple-text-headline">Tạo Đợt Thu Quỹ Mới</h3>
          </div>
          <button
            onClick={() => setIsCreateCampaignModalOpen(false)}
            className="p-1.5 rounded-full text-neutral-400 hover:text-white bg-white/[0.06] hover:bg-white/[0.12] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="space-y-1">
            <label className="font-semibold text-neutral-300">Tên đợt thu *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="VD: Quỹ hoạt động tháng 11 & Thi học kì"
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white text-xs sm:text-sm focus:outline-none focus:border-sky-400"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="font-semibold text-neutral-300">Mức tiền / Học sinh (VND) *</label>
            <input
              type="number"
              step="10000"
              min="10000"
              value={expectedAmount}
              onChange={(e) => setExpectedAmount(Number(e.target.value))}
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white font-mono text-xs sm:text-sm focus:outline-none focus:border-sky-400"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="font-semibold text-neutral-300">Hạn chót đóng quỹ *</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white text-xs sm:text-sm focus:outline-none focus:border-sky-400"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="font-semibold text-neutral-300">Mục đích thu chi</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Ghi chú chi tiết cho học sinh & phụ huynh..."
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white text-xs sm:text-sm focus:outline-none focus:border-sky-400"
            />
          </div>

          <div className="pt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsCreateCampaignModalOpen(false)}
              className="flex-1 py-2.5 rounded-full apple-btn-secondary text-neutral-300 font-medium"
            >
              Hủy
            </button>
            <button
              type="submit"
              className="flex-1 py-2.5 rounded-full apple-btn-primary font-bold shadow-lg shadow-sky-600/30"
            >
              Kích hoạt Đợt thu
            </button>
          </div>
        </form>
        </LiquidGlassCard>
      </div>
    </div>
  );
};
