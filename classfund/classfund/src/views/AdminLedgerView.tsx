import React, { useState, useEffect, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND } from '../data/mockDatabase';
import { 
  Search, 
  TrendingUp, 
  TrendingDown, 
  RotateCcw, 
  Layers,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  Download,
  Filter,
  X,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { adminApi, AdminStats } from '../lib/adminApi';

export const AdminLedgerView: React.FC = () => {
  const { currentUser, currentUserFrontendRole, setSelectedTransaction, addToast } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'ALL' | 'CREDIT' | 'DEBIT' | 'REVERT'>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'VERIFIED' | 'NEEDS_REVIEW' | 'REVERTED' | 'REJECTED' | 'DUPLICATE'>('ALL');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);

  const loadTransactions = async () => {
    try {
      setLoading(true);
      setError(null);
      const offset = (page - 1) * pageSize;
      const data = await adminApi.getAuditLogs({
        limit: pageSize,
        offset,
        entityType: 'TRANSACTION',
      });
      setTransactions(data.items);
      setTotalPages(Math.ceil(data.total / pageSize));
    } catch (err: any) {
      setError(err.message || 'Không thể tải giao dịch');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [page, typeFilter, statusFilter, searchQuery]);

  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const exportTransactions = async () => {
    setExportLoading(true);
    setExportError(null);
    
    try {
      // Fetch all transactions across all pages with current filters
      const allTransactions: any[] = [];
      let page = 1;
      const pageSize = 100;
      let hasMore = true;
      
      while (hasMore) {
        const data = await adminApi.getAuditLogs({
          limit: pageSize,
          offset: (page - 1) * pageSize,
          entityType: 'TRANSACTION',
        });
        allTransactions.push(...data.items);
        hasMore = data.items.length === pageSize;
        page++;
        
        // Safety limit
        if (allTransactions.length >= 50000) break;
      }
      
      // Generate CSV with proper escaping
      const headers = ['Thời gian', 'Loại', 'Mã GD', 'Người gửi', 'Số tiền', 'Trạng thái', 'Nguồn', 'Ghi chú'];
      
      const escapeCsv = (value: string): string => {
        if (!value) return '';
        // Escape quotes by doubling them
        let escaped = value.replace(/"/g, '""');
        // Wrap in quotes if contains comma, quote, newline, or formula injection chars
        if (/[",\n\r]/.test(escaped) || /^[=+\-@]/.test(escaped.trim())) {
          escaped = `"${escaped}"`;
        }
        // Prevent formula injection for untrusted text fields
        if (/^[=+\-@]/.test(escaped.trim())) {
          escaped = `'` + escaped;
        }
        return escaped;
      };
      
      const rows = allTransactions.map(tx => [
        escapeCsv(tx.created_at || ''),
        escapeCsv(tx.type || ''),
        escapeCsv(tx.transaction_code || ''),
        escapeCsv(tx.sender_name || ''),
        escapeCsv(tx.amount ? tx.amount.toString() : ''),
        escapeCsv(tx.status || ''),
        escapeCsv(tx.source || ''),
        escapeCsv(tx.note || ''),
      ]);
      
      const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
      
      // Add UTF-8 BOM for Excel compatibility
      const bom = '\uFEFF';
      const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `ledger_export_${new Date().toISOString().split('T')[0]}.csv`;
      link.click();
      
      addToast({ type: 'success', title: 'Xuất CSV thành công', description: `Đã xuất ${allTransactions.length} bản ghi` });
    } catch (err: any) {
      setExportError(err.message || 'Không thể xuất CSV');
      addToast({ type: 'error', title: 'Lỗi xuất CSV', description: err.message });
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <div className="space-y-6 md:space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-widest block">
            Immutable Financial Ledger
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight apple-text-headline">
            Quản Lý Sổ Cái (Admin)
          </h1>
          <p className="text-xs sm:text-sm text-neutral-400 mt-1">
            Xem, lọc và xuất toàn bộ giao dịch. Chỉ OWNER_TREASURER có thể tạo giao dịch thủ công.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {(currentUserFrontendRole === 'TREASURER') && (
            <button
              onClick={() => addToast({ type: 'info', title: 'Tính năng', description: 'Tạo giao dịch thủ công sẽ được tích hợp sớm' })}
              className="flex-1 sm:flex-none min-h-[44px] px-5 py-2.5 rounded-full bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 font-medium text-xs flex items-center justify-center gap-1.5 border border-emerald-500/25 active:scale-95 transition-all"
            >
              <TrendingUp className="w-4 h-4" />
              <span>Nạp thủ công</span>
            </button>
          )}
          <button
            onClick={exportTransactions}
            disabled={transactions.length === 0 || exportLoading}
            className="flex-1 sm:flex-none min-h-[44px] px-5 py-2.5 rounded-full apple-btn-secondary text-xs sm:text-sm flex items-center justify-center gap-2 active:scale-95 transition-all disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{exportLoading ? 'Đang xuất...' : 'Xuất CSV'}</span>
          </button>
          <button
            onClick={loadTransactions}
            disabled={loading}
            className="flex-1 sm:flex-none min-h-[44px] px-5 py-2.5 rounded-full apple-btn-secondary text-xs sm:text-sm flex items-center justify-center gap-2 active:scale-95 transition-all"
          >
            <Search className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Làm mới</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <LiquidCard variant="clear" className="p-2.5 sm:p-3">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-neutral-400 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm theo mã GD, người gửi, ghi chú..."
              className="w-full pl-11 pr-4 py-2.5 rounded-full bg-white/[0.06] border border-white/15 text-white placeholder-neutral-400 text-xs sm:text-sm focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all font-medium"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as any)}
              className="px-3 py-2 rounded-full bg-white/[0.06] border border-white/15 text-white text-xs font-medium focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all"
            >
              <option value="ALL">Tất cả loại</option>
              <option value="CREDIT">Nạp quỹ (+)</option>
              <option value="DEBIT">Chi quỹ (-)</option>
              <option value="REVERT">Thu hồi</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="px-3 py-2 rounded-full bg-white/[0.06] border border-white/15 text-white text-xs font-medium focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all"
            >
              <option value="ALL">Tất cả trạng thái</option>
              <option value="VERIFIED">Đã duyệt</option>
              <option value="NEEDS_REVIEW">Cần duyệt</option>
              <option value="REVERTED">Đã thu hồi</option>
              <option value="REJECTED">Từ chối</option>
              <option value="DUPLICATE">Trùng lặp</option>
            </select>
          </div>
        </div>
      </LiquidCard>

      {/* Table */}
      <LiquidCard variant="clear" className="p-0 overflow-hidden shadow-2xl">
        {loading && transactions.length === 0 ? (
          <div className="p-12 text-center">
            <Layers className="w-8 h-8 text-sky-400 animate-spin mx-auto mb-3" />
            <p className="text-sm font-medium text-neutral-300">Đang tải giao dịch...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <X className="w-8 h-8 text-rose-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-white mb-1">Không thể tải dữ liệu</p>
            <p className="text-xs text-neutral-400 mb-4">{error}</p>
            <button onClick={loadTransactions} className="px-4 py-2 rounded-lg apple-btn-primary text-sm">
              Thử lại
            </button>
          </div>
        ) : transactions.length === 0 ? (
          <div className="p-12 text-center">
            <Layers className="w-8 h-8 text-neutral-600 mx-auto" />
            <p className="text-sm font-semibold text-neutral-300 mt-2">Không tìm thấy giao dịch nào</p>
            <p className="text-xs text-neutral-500 mt-1">Thử điều chỉnh bộ lọc hoặc tìm kiếm</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/[0.08] text-[11px] font-semibold text-neutral-400 uppercase tracking-widest bg-white/[0.02]">
                  <th className="py-3 px-4 sm:px-6">Thời gian</th>
                  <th className="py-3 px-4">Loại</th>
                  <th className="py-3 px-4">Mã giao dịch</th>
                  <th className="py-3 px-4">Người gửi / Đối tượng</th>
                  <th className="py-3 px-4 text-right">Số tiền</th>
                  <th className="py-3 px-4 text-center">Trạng thái</th>
                  <th className="py-3 px-4">Nguồn</th>
                  <th className="py-3 px-4 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] text-xs sm:text-sm">
                {transactions.map((tx) => {
                  const isCredit = tx.type === 'CREDIT';
                  const isRevert = tx.type === 'REVERT' || tx.status === 'REVERTED';

                  return (
                    <tr
                      key={tx.id}
                      onClick={() => setSelectedTransaction(tx)}
                      className="hover:bg-white/[0.05] transition-colors cursor-pointer group"
                    >
                      <td className="py-3.5 px-4 sm:px-6 text-neutral-400 font-tabular whitespace-nowrap">
                        {new Date(tx.created_at).toLocaleString('vi-VN')}
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                          isRevert ? 'text-amber-400' : isCredit ? 'text-emerald-400' : 'text-rose-400'
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

                      <td className="py-3.5 px-4 font-mono font-medium text-neutral-200 whitespace-nowrap">
                        {tx.transaction_code}
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">{tx.sender_name}</div>
                        {tx.note && (
                          <div className="text-[11px] text-neutral-400 truncate max-w-xs">{tx.note}</div>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-right font-bold font-tabular whitespace-nowrap">
                        <span className={isRevert ? 'text-amber-400' : isCredit ? 'text-emerald-400' : 'text-rose-400'}>
                          {isCredit ? '+' : '-'}{formatVND(tx.amount)}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                          tx.status === 'VERIFIED'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : tx.status === 'NEEDS_REVIEW'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            : tx.status === 'REVERTED'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            : tx.status === 'DUPLICATE'
                            ? 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        }`}>
                          {tx.status === 'VERIFIED' && '✓ Đã duyệt'}
                          {tx.status === 'NEEDS_REVIEW' && '⚠ Cần duyệt'}
                          {tx.status === 'REVERTED' && '↻ Đã thu hồi'}
                          {tx.status === 'DUPLICATE' && '✕ Trùng'}
                          {tx.status === 'REJECTED' && '✕ Từ chối'}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                          tx.source === 'IMAGE' ? 'bg-sky-500/10 text-sky-400 border-sky-500/20' :
                          tx.source === 'MANUAL' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                          'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}>
                          {tx.source}
                        </span>
                      </td>

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

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-white/[0.08] flex items-center justify-between">
            <div className="text-xs text-neutral-400">
              Trang {page} / {totalPages} • {transactions.length} kết quả
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1 || loading}
                className="p-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-neutral-400 disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages || loading}
                className="p-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-neutral-400 disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </LiquidCard>
    </div>
  );
};