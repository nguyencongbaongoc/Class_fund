import React, { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND } from '../data/mockDatabase';
import { StudentRosterItem } from '../types';
import { 
  Users, 
  Search, 
  CheckCircle2, 
  Clock, 
  Plus
} from 'lucide-react';

export const CampaignView: React.FC = () => {
  const { campaign, studentsRoster, markStudentPaid, currentUser, setIsCreateCampaignModalOpen } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'PAID' | 'UNPAID'>('ALL');

  const filteredStudents = useMemo(() => {
    return studentsRoster.filter((student) => {
      if (statusFilter === 'PAID' && student.status !== 'PAID') return false;
      if (statusFilter === 'UNPAID' && student.status !== 'UNPAID') return false;
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchName = student.full_name.toLowerCase().includes(query);
        const matchCode = student.student_code.toLowerCase().includes(query);
        if (!matchName && !matchCode) return false;
      }
      return true;
    });
  }, [studentsRoster, statusFilter, searchQuery]);

  const percentage = Math.round((campaign.paid_students_count / campaign.target_students_count) * 100);

  return (
    <div className="space-y-6 md:space-y-8 animate-in fade-in duration-300">
      {/* Campaign Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-sky-400 uppercase tracking-widest">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Đợt thu đang diễn ra</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1 apple-text-headline">
            {campaign.title}
          </h1>
          <p className="text-xs sm:text-sm text-neutral-400 mt-1 max-w-2xl leading-relaxed">
            {campaign.description}
          </p>
        </div>

        {currentUser.role === 'TREASURER' && (
          <button
            onClick={() => setIsCreateCampaignModalOpen(true)}
            className="self-start sm:self-auto min-h-[44px] px-5 py-2 rounded-full apple-btn-primary font-medium text-xs sm:text-sm flex items-center gap-2 shadow-lg shadow-sky-600/25 active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Tạo đợt thu mới</span>
          </button>
        )}
      </div>

      {/* Progress & Stat Cards (Bento) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Progress Card - Frosted Liquid Glass */}
        <LiquidCard variant="elevated" clarity="frosted" className="md:col-span-2 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-neutral-400">Tiến độ hoàn thành</span>
              <span className="text-sm font-bold text-sky-400 font-tabular">{percentage}%</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl sm:text-4xl font-extrabold text-white font-tabular apple-text-headline">
                {campaign.paid_students_count}
              </span>
              <span className="text-sm text-neutral-400 font-normal">/ {campaign.target_students_count} học sinh đã nộp</span>
            </div>
          </div>

          <div className="mt-5 space-y-2">
            <div className="w-full h-2.5 rounded-full bg-white/[0.08] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-sky-500 to-sky-400 transition-all duration-700"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-neutral-400 pt-1">
              <span>Hạn đóng: {campaign.end_at}</span>
              <span>Còn lại: {campaign.target_students_count - campaign.paid_students_count} bạn</span>
            </div>
          </div>
        </LiquidCard>

        {/* Expected Amount Card - Clear Liquid Glass */}
        <LiquidCard variant="clear" clarity="clear" className="flex flex-col justify-between">
          <div>
            <span className="text-xs font-medium text-neutral-400">Mức thu định mức</span>
            <p className="text-2xl sm:text-3xl font-bold text-white mt-1.5 font-tabular">
              {formatVND(campaign.expected_amount_per_student)}
            </p>
            <p className="text-xs text-neutral-400 mt-1">Mỗi học sinh trong danh sách</p>
          </div>

          <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between text-xs">
            <span className="text-neutral-400">Đã thu về:</span>
            <span className="text-emerald-400 font-bold font-tabular">{formatVND(campaign.total_collected_amount)}</span>
          </div>
        </LiquidCard>
      </div>

      {/* Roster Table Card */}
      <LiquidCard className="p-4 sm:p-6 space-y-4">
        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-neutral-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm theo tên học sinh, số thứ tự..."
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-white/[0.04] border border-white/10 text-white placeholder-neutral-400 text-xs sm:text-sm focus:outline-none focus:border-sky-400 transition-colors"
            />
          </div>

          {/* Segmented Filter Buttons */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setStatusFilter('ALL')}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                statusFilter === 'ALL'
                  ? 'bg-white/15 text-white font-semibold shadow-sm border border-white/10'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              Tất cả ({studentsRoster.length})
            </button>
            <button
              onClick={() => setStatusFilter('PAID')}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                statusFilter === 'PAID'
                  ? 'bg-white/15 text-emerald-300 font-semibold shadow-sm border border-emerald-500/30'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              Đã nộp ({campaign.paid_students_count})
            </button>
            <button
              onClick={() => setStatusFilter('UNPAID')}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                statusFilter === 'UNPAID'
                  ? 'bg-white/15 text-rose-300 font-semibold shadow-sm border border-rose-500/30'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              Chưa nộp ({campaign.target_students_count - campaign.paid_students_count})
            </button>
          </div>
        </div>

        {/* Roster List Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/[0.08] text-[11px] font-semibold text-neutral-400 uppercase tracking-widest">
                <th className="py-3 px-3 sm:px-4">Mã HS</th>
                <th className="py-3 px-4">Họ và tên</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                <th className="py-3 px-4 text-right">Số tiền</th>
                <th className="py-3 px-4">Mã giao dịch / Ghi chú</th>
                {(currentUser.role === 'TREASURER' || currentUser.role === 'MODERATOR') && (
                  <th className="py-3 px-4 text-right">Thao tác</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-xs sm:text-sm">
              {filteredStudents.map((student) => {
                const isPaid = student.status === 'PAID';

                return (
                  <tr key={student.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3.5 px-3 sm:px-4 font-mono text-neutral-400">{student.student_code}</td>
                    <td className="py-3.5 px-4 font-semibold text-white">{student.full_name}</td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      {isPaid ? (
                        <span className="text-emerald-400 font-medium inline-flex items-center gap-1 text-xs">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Đã nộp</span>
                        </span>
                      ) : (
                        <span className="text-neutral-400 font-medium inline-flex items-center gap-1 text-xs">
                          <Clock className="w-3.5 h-3.5 text-neutral-500" />
                          <span>Chưa nộp</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right font-tabular font-semibold">
                      {isPaid ? (
                        <span className="text-emerald-400">+{formatVND(student.matched_amount || campaign.expected_amount_per_student)}</span>
                      ) : (
                        <span className="text-neutral-600">—</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-neutral-300 font-mono text-xs">
                      {student.matched_transaction_code ? (
                        <span className="text-sky-300">{student.matched_transaction_code}</span>
                      ) : (
                        <span className="text-neutral-500 italic">{student.notes || '—'}</span>
                      )}
                    </td>
                    {(currentUser.role === 'TREASURER' || currentUser.role === 'MODERATOR') && (
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <button
                          onClick={() => markStudentPaid(student.id, !isPaid)}
                          className={`px-3 py-1 rounded-full text-[11px] font-medium transition-all ${
                            isPaid
                              ? 'bg-rose-500/10 text-rose-300 hover:bg-rose-500/20'
                              : 'bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20'
                          }`}
                        >
                          {isPaid ? 'Bỏ nộp' : 'Thu tiền mặt'}
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </LiquidCard>
    </div>
  );
};
