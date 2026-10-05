import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { 
  Search, 
  Filter, 
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  Calendar,
  User,
  Database,
  RotateCcw,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  XCircle,
  MoreVertical
} from 'lucide-react';
import { adminApi, AuditLogItem, PaginatedAuditLogs } from '../lib/adminApi';

export const AuditLogView: React.FC = () => {
  const { currentUser, addToast } = useApp();
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Filters
  const [filters, setFilters] = useState({
    action: '',
    entityType: '',
    entityId: '',
    actorId: '',
    dateFrom: '',
    dateTo: '',
  });

  const [actionOptions, setActionOptions] = useState<string[]>([]);
  const [entityTypeOptions, setEntityTypeOptions] = useState<string[]>([]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const offset = (page - 1) * pageSize;
      const data = await adminApi.getAuditLogs({
        limit: pageSize,
        offset,
        action: filters.action || undefined,
        entityType: filters.entityType || undefined,
        entityId: filters.entityId || undefined,
        actorId: filters.actorId || undefined,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
      });
      setLogs(data.items);
      setTotalItems(data.total);
      setTotalPages(Math.ceil(data.total / pageSize));

      // Collect unique action and entity_type values for filter dropdowns
      if (data.items.length > 0) {
        const actions = [...new Set(data.items.map(l => l.action).filter(Boolean))].sort();
        const entityTypes = [...new Set(data.items.map(l => l.entityType).filter(Boolean))].sort();
        setActionOptions(actions);
        setEntityTypeOptions(entityTypes);
      }
    } catch (err: any) {
      setError(err.message || 'Không thể tải nhật ký kiểm toán');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({
      action: '',
      entityType: '',
      entityId: '',
      actorId: '',
      dateFrom: '',
      dateTo: '',
    });
    setPage(1);
  };

  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const exportLogs = async () => {
    setExportLoading(true);
    setExportError(null);

    try {
      // Use backend export endpoint for complete filtered result set
      const result = await adminApi.exportAuditLogs({
        action: filters.action || undefined,
        entityType: filters.entityType || undefined,
        entityId: filters.entityId || undefined,
        actorId: filters.actorId || undefined,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
        limit: 50000,
      });

      // Backend already generates properly escaped CSV with UTF-8 BOM
      const bom = '\uFEFF';
      const blob = new Blob([bom + result.csv_content], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = result.filename;
      link.click();

      addToast({ type: 'success', title: 'Xuất CSV thành công', description: `Đã xuất ${result.total_records} bản ghi` });
    } catch (err: any) {
      setExportError(err.message || 'Không thể xuất CSV');
      addToast({ type: 'error', title: 'Lỗi xuất CSV', description: err.message });
    } finally {
      setExportLoading(false);
    }
  };

  const getActionIcon = (action: string) => {
    if (action.includes('CREATE') || action.includes('POST')) return <TrendingUp className="w-4 h-4 text-emerald-400" />;
    if (action.includes('REVERT') || action.includes('DELETE')) return <RotateCcw className="w-4 h-4 text-amber-400" />;
    if (action.includes('UPDATE') || action.includes('EDIT')) return <Database className="w-4 h-4 text-sky-400" />;
    if (action.includes('LOGIN') || action.includes('AUTH')) return <User className="w-4 h-4 text-sky-400" />;
    return <AlertTriangle className="w-4 h-4 text-neutral-400" />;
  };

  const getActionColor = (action: string) => {
    if (action.includes('CREATE') || action.includes('POST') || action.includes('CREDIT')) return 'text-emerald-400';
    if (action.includes('REVERT') || action.includes('DEBIT') || action.includes('REJECT')) return 'text-rose-400';
    if (action.includes('UPDATE') || action.includes('APPROVE')) return 'text-sky-400';
    if (action.includes('LOGIN')) return 'text-sky-400';
    return 'text-neutral-300';
  };

  useEffect(() => {
    loadLogs();
  }, [page, filters]);

  return (
    <div className="space-y-6 md:space-y-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium tracking-wide text-neutral-400">
            <Database className="w-4 h-4 text-sky-400" />
            <span>Nhật ký kiểm toán</span>
            <span aria-hidden="true" className="text-neutral-600">·</span>
            <span>Lịch sử bất biến</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white apple-text-headline">
            Audit Log
          </h1>
          <p className="text-sm text-neutral-400">
            {totalItems} bản ghi. Tất cả thay đổi tài chính, duyệt AI và hành động admin đều được ghi lại.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={exportLogs}
            disabled={logs.length === 0}
            className="flex-1 sm:flex-none min-h-[44px] px-5 py-2.5 rounded-full apple-btn-secondary text-xs sm:text-sm flex items-center justify-center gap-2 active:scale-95 transition-all disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>Xuất CSV</span>
          </button>
          <button
            onClick={loadLogs}
            disabled={loading}
            className="flex-1 sm:flex-none min-h-[44px] px-5 py-2.5 rounded-full apple-btn-secondary text-xs sm:text-sm flex items-center justify-center gap-2 active:scale-95 transition-all"
          >
            <Search className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Làm mới</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <LiquidCard variant="clear" className="p-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-neutral-400 block mb-1">Hành động</label>
            <select
              value={filters.action}
              onChange={(e) => handleFilterChange('action', e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-white/[0.06] border border-white/15 text-white text-sm focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all"
            >
              <option value="">Tất cả hành động</option>
              {actionOptions.map(action => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-neutral-400 block mb-1">Loại thực thể</label>
            <select
              value={filters.entityType}
              onChange={(e) => handleFilterChange('entityType', e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-white/[0.06] border border-white/15 text-white text-sm focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all"
            >
              <option value="">Tất cả loại</option>
              {entityTypeOptions.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-neutral-400 block mb-1">ID thực thể</label>
            <input
              type="text"
              value={filters.entityId}
              onChange={(e) => handleFilterChange('entityId', e.target.value)}
              placeholder="ID giao dịch, upload, v.v."
              className="w-full px-3 py-2 rounded-lg bg-white/[0.06] border border-white/15 text-white placeholder-neutral-400 text-sm focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all"
            />
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-neutral-400 block mb-1">Người thực hiện</label>
            <input
              type="text"
              value={filters.actorId}
              onChange={(e) => handleFilterChange('actorId', e.target.value)}
              placeholder="User ID"
              className="w-full px-3 py-2 rounded-lg bg-white/[0.06] border border-white/15 text-white placeholder-neutral-400 text-sm focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all"
            />
          </div>

          <div className="flex-1 min-w-[180px]">
            <label className="text-xs text-neutral-400 block mb-1">Từ ngày</label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-white/[0.06] border border-white/15 text-white text-sm focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all"
            />
          </div>

          <div className="flex-1 min-w-[180px]">
            <label className="text-xs text-neutral-400 block mb-1">Đến ngày</label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => handleFilterChange('dateTo', e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-white/[0.06] border border-white/15 text-white text-sm focus:outline-none focus:border-sky-400 focus:bg-white/[0.10] transition-all"
            />
          </div>

          <button
            onClick={clearFilters}
            className="h-10 px-4 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 font-medium text-sm flex items-center justify-center gap-1.5 border border-rose-500/25 active:scale-95 transition-all"
          >
            <XCircle className="w-4 h-4" />
            <span>Xóa bộ lọc</span>
          </button>
        </div>
      </LiquidCard>

      {/* Table */}
      <LiquidCard variant="clear" className="p-0 overflow-hidden shadow-2xl">
        {loading && logs.length === 0 ? (
          <div className="p-12 text-center">
            <Database className="w-8 h-8 text-sky-400 animate-spin mx-auto mb-3" />
            <p className="text-sm font-medium text-neutral-300">Đang tải nhật ký...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <XCircle className="w-8 h-8 text-rose-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-white mb-1">Không thể tải dữ liệu</p>
            <p className="text-xs text-neutral-400 mb-4">{error}</p>
            <button onClick={loadLogs} className="px-4 py-2 rounded-lg apple-btn-primary text-sm">
              Thử lại
            </button>
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center">
            <Database className="w-8 h-8 text-neutral-600 mx-auto" />
            <p className="text-sm font-semibold text-neutral-300 mt-2">Không tìm thấy bản ghi nào</p>
            <p className="text-xs text-neutral-500 mt-1">Thử điều chỉnh bộ lọc</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/[0.08] text-[11px] font-semibold text-neutral-400 uppercase tracking-widest bg-white/[0.02]">
                  <th className="py-3 px-4 sm:px-6">Thời gian</th>
                  <th className="py-3 px-4">Hành động</th>
                  <th className="py-3 px-4">Loại thực thể</th>
                  <th className="py-3 px-4">ID thực thể</th>
                  <th className="py-3 px-4">Người thực hiện</th>
                  <th className="py-3 px-4">IP</th>
                  <th className="py-3 px-4 text-right">Chi tiết</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] text-xs sm:text-sm">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/[0.05] transition-colors">
                    <td className="py-3.5 px-4 sm:px-6 text-neutral-400 font-tabular whitespace-nowrap">
                      {new Date(log.createdAt).toLocaleString('vi-VN')}
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        {getActionIcon(log.action)}
                        <span className={`font-medium ${getActionColor(log.action)}`}>{log.action}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-neutral-300">{log.entityType}</td>

                    <td className="py-3.5 px-4 font-mono text-neutral-200 truncate max-w-xs">
                      {log.entityId || '—'}
                    </td>

                    <td className="py-3.5 px-4">
                      <div>
                        <span className="font-medium text-white">{log.actorName || 'Hệ thống'}</span>
                        {log.actorRole && (
                          <div className="text-[10px] text-neutral-400">{log.actorRole}</div>
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-neutral-400 font-mono text-[11px]">
                      {log.ip || '—'}
                    </td>

                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => {
                          const detail = `Hành động: ${log.action}\nThực thể: ${log.entityType} (${log.entityId})\nNgười thực hiện: ${log.actorName || 'System'} (${log.actorRole || 'N/A'})\nThời gian: ${new Date(log.createdAt).toLocaleString('vi-VN')}\nIP: ${log.ip || 'N/A'}\n\nTrước:\n${log.beforeData ? JSON.stringify(log.beforeData, null, 2) : 'Không có'}\n\nSau:\n${log.afterData ? JSON.stringify(log.afterData, null, 2) : 'Không có'}`;
                          alert(detail);
                        }}
                        className="text-xs font-medium text-sky-400 hover:text-sky-300 hover:underline flex items-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Xem</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-white/[0.08] flex items-center justify-between">
            <div className="text-xs text-neutral-400">
              Trang {page} / {totalPages} • Tổng {totalItems} bản ghi
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