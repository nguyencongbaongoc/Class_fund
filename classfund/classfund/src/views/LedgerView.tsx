import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND } from '../data/mockDatabase';
import { 
  Search, 
  TrendingUp, 
  TrendingDown, 
  RotateCcw, 
  Layers
} from 'lucide-react';

export const LedgerView: React.FC = () => {
  const { ledgerEntries, setSelectedTransaction, balances } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'ALL' | 'CREDIT' | 'DEBIT' | 'REVERT'>('ALL');
  const [statusFilter] = useState<'ALL' | 'VERIFIED' | 'NEEDS_REVIEW' | 'REVERTED'>('ALL');
  const [slideDirection, setSlideDirection] = useState<'right' | 'left'>('right');

  const tabContainerRef = useRef<HTMLDivElement>(null);
  const tableScrollRef = useRef<HTMLDivElement>(null);
  const isSyncingScroll = useRef(false);

  const [indicatorStyle, setIndicatorStyle] = useState<{ left: number; width: number; opacity: number }>({
    left: 0,
    width: 0,
    opacity: 0,
  });

  const filterIndices: Record<string, number> = {
    'ALL': 0,
    'CREDIT': 1,
    'DEBIT': 2,
    'REVERT': 3,
  };

  const handleFilterChange = (newFilter: typeof typeFilter) => {
    if (filterIndices[newFilter] >= filterIndices[typeFilter]) {
      setSlideDirection('right');
    } else {
      setSlideDirection('left');
    }
    setTypeFilter(newFilter);
  };

  // Synchronized horizontal scroll: When sliding top bar, bottom table also slides
  const handleTopScroll = () => {
    if (isSyncingScroll.current) return;
    isSyncingScroll.current = true;
    if (tabContainerRef.current && tableScrollRef.current) {
      const maxTop = tabContainerRef.current.scrollWidth - tabContainerRef.current.clientWidth;
      const maxTable = tableScrollRef.current.scrollWidth - tableScrollRef.current.clientWidth;
      if (maxTop > 0 && maxTable > 0) {
        const ratio = tabContainerRef.current.scrollLeft / maxTop;
        tableScrollRef.current.scrollLeft = ratio * maxTable;
      }
    }
    setTimeout(() => { isSyncingScroll.current = false; }, 40);
  };

  const handleTableScroll = () => {
    if (isSyncingScroll.current) return;
    isSyncingScroll.current = true;
    if (tabContainerRef.current && tableScrollRef.current) {
      const maxTop = tabContainerRef.current.scrollWidth - tabContainerRef.current.clientWidth;
      const maxTable = tableScrollRef.current.scrollWidth - tableScrollRef.current.clientWidth;
      if (maxTop > 0 && maxTable > 0) {
        const ratio = tableScrollRef.current.scrollLeft / maxTable;
        tabContainerRef.current.scrollLeft = ratio * maxTop;
      }
    }
    setTimeout(() => { isSyncingScroll.current = false; }, 40);
  };

  // Smooth sliding pill indicator animation when filter changes
  useEffect(() => {
    const updatePill = () => {
      if (tabContainerRef.current) {
        const activeBtn = tabContainerRef.current.querySelector<HTMLElement>(`[data-filter="${typeFilter}"]`);
        if (activeBtn) {
          setIndicatorStyle({
            left: activeBtn.offsetLeft,
            width: activeBtn.offsetWidth,
            opacity: 1,
          });
        }
      }
    };

    updatePill();
    window.addEventListener('resize', updatePill);
    return () => window.removeEventListener('resize', updatePill);
  }, [typeFilter]);

  const filteredEntries = useMemo(() => {
    return ledgerEntries.filter((tx) => {
      // Type match
      if (typeFilter !== 'ALL') {
        if (typeFilter === 'REVERT' && tx.type !== 'REVERT' && tx.status !== 'REVERTED') return false;
        if (typeFilter === 'CREDIT' && tx.type !== 'CREDIT') return false;
        if (typeFilter === 'DEBIT' && tx.type !== 'DEBIT') return false;
      }

      // Status match
      if (statusFilter !== 'ALL' && tx.status !== statusFilter) return false;

      // Search match
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchCode = tx.transaction_code.toLowerCase().includes(query);
        const matchSender = tx.sender_name.toLowerCase().includes(query);
        const matchNote = tx.note?.toLowerCase().includes(query);
        const matchUploader = tx.uploaded_by.toLowerCase().includes(query);
        if (!matchCode && !matchSender && !matchNote && !matchUploader) return false;
      }

      return true;
    });
  }, [ledgerEntries, typeFilter, statusFilter, searchQuery]);

  return (
    <div className="space-y-6 md:space-y-8 animate-in fade-in duration-300">
      {/* Header and Summary Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-widest block">
            Immutable Financial Ledger
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight apple-text-headline">
            Sổ Cái Kế Toán Quỹ Lớp.
          </h1>
          <p className="text-xs sm:text-sm text-neutral-400 mt-1">
            Bút toán nạp, chi và thu hồi (revert) được bảo vệ bởi kỹ thuật băm vân tay và khóa bất biến.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-5 py-2.5 rounded-2xl apple-frosted-glass text-right border border-white/10">
            <span className="text-[10px] text-neutral-400 uppercase tracking-widest block font-medium">Số dư hiện tại</span>
            <span className="text-lg font-bold text-white font-tabular">{formatVND(balances.currentBalance)}</span>
          </div>
        </div>
      </div>

      {/* Top Filter and Search Bar with Unified Horizontal Liquid Glass & Sliding Pill */}
      <LiquidCard variant="clear" className="p-2.5 sm:p-3">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          {/* Search box with pill style */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-neutral-400 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm theo mã giao dịch, người gửi, ghi chú..."
              className="w-full pl-11 pr-4 py-2.5 rounded-full bg-white/[0.06] border border-white/15 text-white placeholder-neutral-400 text-xs sm:text-sm focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all font-medium"
            />
          </div>

          {/* Interactive filter tabs with Smooth Sliding Pill Indicator and Scroll Sync */}
          <div 
            ref={tabContainerRef}
            onScroll={handleTopScroll}
            className="relative flex items-center bg-black/25 backdrop-blur-2xl border border-white/15 rounded-full p-1 shadow-inner shrink-0 overflow-x-auto scrollbar-none"
          >
            {/* Smooth Sliding Pill Indicator with Apple Spring Physics */}
            <div
              className="absolute top-1 bottom-1 rounded-full border border-white/50 bg-white/20 shadow-[0_2px_12px_rgba(255,255,255,0.25)] pointer-events-none transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] z-0"
              style={{
                left: `${indicatorStyle.left}px`,
                width: `${indicatorStyle.width}px`,
                opacity: indicatorStyle.opacity,
              }}
            />

            {(['ALL', 'CREDIT', 'DEBIT', 'REVERT'] as const).map((filter) => {
              const labels = {
                ALL: 'Tất cả',
                CREDIT: 'Nạp quỹ (+)',
                DEBIT: 'Chi quỹ (-)',
                REVERT: 'Đã thu hồi (Revert)'
              };
              const isSelected = typeFilter === filter;
              return (
                <button
                  key={filter}
                  data-filter={filter}
                  onClick={() => handleFilterChange(filter)}
                  className={`relative z-10 px-3.5 sm:px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all duration-200 active:scale-95 ${
                    isSelected
                      ? 'text-white font-bold drop-shadow-sm'
                      : 'text-neutral-300 hover:text-white'
                  }`}
                >
                  {labels[filter]}
                </button>
              );
            })}
          </div>
        </div>
      </LiquidCard>

      {/* Table Content: Synchronized Directional Slide with Apple Spring Physics */}
      <div 
        key={typeFilter} 
        className={slideDirection === 'right' ? 'animate-slide-from-right' : 'animate-slide-from-left'}
      >
        <LiquidCard variant="clear" className="p-0 overflow-hidden shadow-2xl">
          {filteredEntries.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <Layers className="w-8 h-8 text-neutral-600 mx-auto" />
              <p className="text-sm font-semibold text-neutral-300">Không tìm thấy giao dịch nào</p>
              <p className="text-xs text-neutral-500">Thử tìm kiếm với từ khóa khác hoặc xóa bộ lọc</p>
            </div>
          ) : (
            <div 
              ref={tableScrollRef}
              onScroll={handleTableScroll}
              className="overflow-x-auto scrollbar-none transition-all duration-300"
            >
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/[0.08] text-[11px] font-semibold text-neutral-400 uppercase tracking-widest bg-white/[0.02]">
                    <th className="py-3 px-4 sm:px-6">Thời gian</th>
                    <th className="py-3 px-4">Loại</th>
                    <th className="py-3 px-4">Mã giao dịch</th>
                    <th className="py-3 px-4">Người gửi / Đối tượng</th>
                    <th className="py-3 px-4 text-right">Số tiền</th>
                    <th className="py-3 px-4 text-center">Trạng thái</th>
                    <th className="py-3 px-4 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] text-xs sm:text-sm">
                  {filteredEntries.map((tx) => {
                    const isCredit = tx.type === 'CREDIT';
                    const isRevert = tx.type === 'REVERT' || tx.status === 'REVERTED';

                    return (
                      <tr
                        key={tx.id}
                        onClick={() => setSelectedTransaction(tx)}
                        className="hover:bg-white/[0.05] transition-colors cursor-pointer group"
                      >
                        {/* Date */}
                        <td className="py-3.5 px-4 sm:px-6 text-neutral-400 font-tabular whitespace-nowrap">
                          {tx.created_at}
                        </td>

                        {/* Type */}
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                            isRevert 
                              ? 'text-amber-400' 
                              : isCredit 
                                ? 'text-emerald-400' 
                                : 'text-rose-400'
                          }`}>
                            {isRevert ? (
                              <RotateCcw className="w-3.5 h-3.5" />
                            ) : isCredit ? (
                              <TrendingUp className="w-3.5 h-3.5" />
                            ) : (
                              <TrendingDown className="w-3.5 h-3.5" />
                            )}
                            <span>{tx.type}</span>
                          </span>
                        </td>

                        {/* Tx Code */}
                        <td className="py-3.5 px-4 font-mono font-medium text-neutral-200 whitespace-nowrap">
                          {tx.transaction_code}
                        </td>

                        {/* Sender */}
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-white">{tx.sender_name}</div>
                          {tx.note && (
                            <div className="text-[11px] text-neutral-400 truncate max-w-xs">{tx.note}</div>
                          )}
                        </td>

                        {/* Amount */}
                        <td className="py-3.5 px-4 text-right font-bold font-tabular whitespace-nowrap">
                          <span className={isRevert ? 'text-amber-400' : isCredit ? 'text-emerald-400' : 'text-rose-400'}>
                            {isCredit ? '+' : '-'}{formatVND(tx.amount)}
                          </span>
                        </td>

                        {/* Status */}
                        <td className="py-3.5 px-4 text-center whitespace-nowrap">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                            tx.status === 'VERIFIED'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : tx.status === 'NEEDS_REVIEW'
                              ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                              : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          }`}>
                            {tx.status === 'VERIFIED' && '✓ Đã duyệt'}
                            {tx.status === 'NEEDS_REVIEW' && '⚠ Cần đối soát'}
                            {tx.status === 'REVERTED' && '⚠ Đã thu hồi'}
                            {tx.status === 'DUPLICATE' && '✕ Trùng lặp'}
                            {tx.status === 'REJECTED' && '✕ Từ chối'}
                          </span>
                        </td>

                        {/* Actions */}
                        <td className="py-3.5 px-4 text-right whitespace-nowrap">
                          <span className="text-xs font-medium text-sky-400 group-hover:text-sky-300 group-hover:underline">
                            Chi tiết &rsaquo;
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </LiquidCard>
      </div>
    </div>
  );
};
