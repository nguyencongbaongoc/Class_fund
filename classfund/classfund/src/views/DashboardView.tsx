import React from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND, ASSET_PATHS } from '../data/mockDatabase';
import { 
  TrendingUp, 
  TrendingDown, 
  QrCode, 
  UploadCloud, 
  ArrowUpRight, 
  Users, 
  ShieldCheck, 
  Clock, 
  MinusCircle, 
  ChevronRight,
  Sparkles
} from 'lucide-react';

export const DashboardView: React.FC = () => {
  const { 
    balances, 
    campaign, 
    ledgerEntries, 
    setCurrentTab, 
    setSelectedTransaction,
    currentUser,
    setIsExpenseModalOpen 
  } = useApp();

  const recentTransactions = ledgerEntries.slice(0, 5);

  return (
    <div className="space-y-8 md:space-y-12">
      {/* Apple-style Keynote Hero Frame with Frosted Ultra-Clear Glass */}
      <LiquidCard variant="clear" className="p-6 sm:p-10 md:p-12 overflow-hidden shadow-2xl">
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-medium tracking-wide text-neutral-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>Sổ quỹ lớp 12A1</span>
              <span aria-hidden="true" className="text-neutral-600">·</span>
              <span>Niên khoá 2026 - 2027</span>
              <span aria-hidden="true" className="text-neutral-600">·</span>
              <span className="text-sky-400">Liquid Glass Optics</span>
            </div>
            
            <h1 className="text-sm sm:text-base text-neutral-400 font-medium">
              Số dư quỹ khả dụng
            </h1>
            
            <div className="flex items-baseline gap-3">
              <span className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white font-tabular apple-text-headline drop-shadow-md">
                {formatVND(balances.currentBalance)}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-400 pt-1">
              <span>Số dư ban đầu: {formatVND(balances.openingBalance)}</span>
              <span aria-hidden="true" className="text-neutral-600">·</span>
              <span>Tính toán tự động từ sổ cái bất biến</span>
            </div>
          </div>

          {/* Apple-style Quick Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setCurrentTab('upload')}
              className="flex-1 sm:flex-none min-h-[44px] px-6 py-2.5 rounded-full apple-btn-primary font-medium text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-sky-600/25 active:scale-95 transition-all"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Nộp biên lai</span>
            </button>

            <button
              onClick={() => setCurrentTab('bank')}
              className="flex-1 sm:flex-none min-h-[44px] px-5 py-2.5 rounded-full apple-btn-secondary text-xs sm:text-sm flex items-center justify-center gap-2 active:scale-95 transition-all"
            >
              <QrCode className="w-4 h-4 text-sky-400" />
              <span>Mã VietQR</span>
            </button>

            {(currentUser.role === 'TREASURER' || currentUser.role === 'MODERATOR') && (
              <button
                onClick={() => setIsExpenseModalOpen(true)}
                className="w-full sm:w-auto min-h-[44px] px-5 py-2.5 rounded-full bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 font-medium text-xs flex items-center justify-center gap-1.5 border border-rose-500/25 active:scale-95 transition-all"
              >
                <MinusCircle className="w-4 h-4" />
                <span>Chi quỹ</span>
              </button>
            )}
          </div>
        </div>
      </LiquidCard>

      {/* Bento Grid Summary Cards (Apple Style) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
        {/* Total Credit - Trong suốt rõ */}
        <LiquidCard variant="clear" clarity="clear" className="flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-neutral-400">Tổng nạp vào quỹ</p>
              <p className="text-2xl sm:text-3xl font-bold text-white mt-1.5 font-tabular">
                +{formatVND(balances.totalCredit)}
              </p>
            </div>
            <div className="w-9 h-9 rounded-full bg-white/[0.06] border border-white/10 flex items-center justify-center text-emerald-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-6 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-neutral-400">
            <span>Từ biên lai chuyển khoản & PH</span>
            <span className="text-emerald-400 font-medium">100% khớp</span>
          </div>
        </LiquidCard>

        {/* Total Debit - Trong suốt rõ */}
        <LiquidCard variant="clear" clarity="clear" className="flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-bold text-sky-200 uppercase tracking-wider">Tổng đã chi & hoàn</p>
              <p className="text-2xl sm:text-3xl font-bold text-white mt-1.5 font-tabular">
                -{formatVND(balances.totalDebit)}
              </p>
            </div>
            <div className="w-9 h-9 rounded-full bg-white/[0.06] border border-white/10 flex items-center justify-center text-rose-400">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-6 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-slate-100 font-medium">
            <span>In đề cương & hoàn trả nhầm</span>
            <span className="text-white font-bold">Có log lưu</span>
          </div>
        </LiquidCard>

        {/* Current Campaign */}
        <LiquidCard 
          className="flex flex-col justify-between sm:col-span-2 lg:col-span-1 cursor-pointer group hover:border-white/20"
          onClick={() => setCurrentTab('campaign')}
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-sky-400">
                <Users className="w-3.5 h-3.5" />
                <span>Đợt thu đang mở</span>
              </div>
              <p className="text-base sm:text-lg font-bold text-white mt-1 line-clamp-1 group-hover:text-sky-300 transition-colors">
                {campaign.title}
              </p>
            </div>
            <ArrowUpRight className="w-4 h-4 text-neutral-400 group-hover:text-white transition-colors" />
          </div>

          <div className="mt-5 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">Tiến độ đóng</span>
              <span className="text-white font-medium font-tabular">
                {campaign.paid_students_count} / {campaign.target_students_count} bạn ({Math.round((campaign.paid_students_count / campaign.target_students_count) * 100)}%)
              </span>
            </div>
            {/* Apple Minimalist Progress Track */}
            <div className="w-full h-2 rounded-full bg-white/[0.08] overflow-hidden">
              <div 
                className="h-full rounded-full bg-gradient-to-r from-sky-500 to-sky-400 transition-all duration-500"
                style={{ width: `${(campaign.paid_students_count / campaign.target_students_count) * 100}%` }}
              />
            </div>
          </div>
        </LiquidCard>
      </div>

      {/* Class Photo Banner (Apple Editorial Style) */}
      <div className="relative rounded-3xl overflow-hidden apple-frosted-glass h-44 sm:h-52 flex items-center justify-between p-6 sm:p-10 border border-white/[0.1]">
        <img 
          src={ASSET_PATHS.classBanner} 
          alt="Tập thể lớp 12A1" 
          referrerPolicy="no-referrer"
          className="absolute inset-0 w-full h-full object-cover opacity-20 filter grayscale mix-blend-screen scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-black via-black/85 to-transparent" />
        
        <div className="relative z-10 max-w-lg space-y-2">
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-widest">Triết Lý Thiết Kế Thượng Lưu</span>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight apple-text-headline">
            Minh bạch tuyệt đối. Đẹp đến từng chi tiết.
          </h2>
          <p className="text-xs sm:text-sm text-neutral-300 line-clamp-2 leading-relaxed">
            Mọi biên lai chuyển khoản được xác thực tự động, đối soát 4 lớp bảo vệ và ghi sổ cái tài chính chuẩn mực.
          </p>
        </div>

        <button
          onClick={() => setCurrentTab('public')}
          className="relative z-10 hidden sm:flex items-center gap-2 px-5 py-2.5 rounded-full apple-btn-secondary text-xs font-medium active:scale-95 transition-all"
        >
          <span>Xem trang công khai</span>
          <ChevronRight className="w-4 h-4 text-neutral-400" />
        </button>
      </div>

      {/* Recent Activity Table (Apple Minimalist Table) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight">Giao dịch gần đây</h3>
            <p className="text-xs text-slate-100 font-medium">Lịch sử ghi sổ cái bất biến</p>
          </div>
          <button
            onClick={() => setCurrentTab('ledger')}
            className="text-xs font-semibold text-sky-400 hover:text-sky-300 flex items-center gap-1 transition-colors"
          >
            <span>Tất cả ({ledgerEntries.length})</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <LiquidCard className="p-0 overflow-hidden">
          <div className="divide-y divide-white/[0.06]">
            {recentTransactions.map((tx) => {
              const isCredit = tx.type === 'CREDIT';
              const isRevert = tx.type === 'REVERT' || tx.status === 'REVERTED';

              return (
                <div
                  key={tx.id}
                  onClick={() => setSelectedTransaction(tx)}
                  className="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-white/[0.03] transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 border ${
                      isRevert 
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' 
                        : isCredit 
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                          : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                    }`}>
                      {isRevert ? (
                        <Clock className="w-4 h-4" />
                      ) : isCredit ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : (
                        <TrendingDown className="w-4 h-4" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-white truncate">{tx.sender_name}</p>
                        {tx.status === 'VERIFIED' && (
                          <span className="text-[10px] text-emerald-400 font-medium">✓ Đã duyệt</span>
                        )}
                        {tx.status === 'REVERTED' && (
                          <span className="text-[10px] text-amber-400 font-medium">⚠ Đã thu hồi</span>
                        )}
                        {tx.status === 'NEEDS_REVIEW' && (
                          <span className="text-[10px] text-sky-400 font-medium">⏳ Cần duyệt</span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-slate-200 mt-0.5 truncate font-medium">
                        <span className="font-mono text-[11px] text-neutral-300">{tx.transaction_code}</span>
                        <span aria-hidden="true" className="text-neutral-600">·</span>
                        <span>{tx.created_at}</span>
                        {tx.extracted_bank && (
                          <>
                            <span aria-hidden="true" className="text-neutral-600">·</span>
                            <span>{tx.extracted_bank}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <p className={`text-sm sm:text-base font-bold font-tabular ${
                      isRevert 
                        ? 'text-amber-400' 
                        : isCredit 
                          ? 'text-emerald-400' 
                          : 'text-rose-400'
                    }`}>
                      {isCredit ? '+' : '-'}{formatVND(tx.amount)}
                    </p>
                    <p className="text-[11px] text-neutral-500 capitalize">{tx.source.toLowerCase()}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </LiquidCard>
      </div>
    </div>
  );
};
