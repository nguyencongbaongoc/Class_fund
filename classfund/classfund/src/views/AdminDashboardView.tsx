import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND } from '../data/mockDatabase';
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
  Sparkles,
  AlertTriangle,
  Server,
  Database,
  HardDrive,
  Cpu,
  Wifi,
  Loader2,
  CheckCircle,
  XCircle,
  RefreshCw,
  BarChart2
} from 'lucide-react';
import { adminApi, AdminStats, WorkerStatus, SystemHealth, QueueStatus } from '../lib/adminApi';

export const AdminDashboardView: React.FC = () => {
  const { 
    currentUser,
    setCurrentTab,
    setIsExpenseModalOpen,
    addToast,
  } = useApp();

  const [stats, setStats] = useState<AdminStats | null>(null);
  const [workers, setWorkers] = useState<WorkerStatus[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [statsRes, workersRes, healthRes, queueRes] = await Promise.allSettled([
        adminApi.getStats(),
        adminApi.getWorkers(),
        adminApi.getHealth(),
        adminApi.getQueueStatus(),
      ]);

      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      if (workersRes.status === 'fulfilled') setWorkers(workersRes.value);
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value);
      if (queueRes.status === 'fulfilled') setQueueStatus(queueRes.value);

      const failed = [statsRes, workersRes, healthRes, queueRes].filter(r => r.status === 'rejected');
      if (failed.length > 0) {
        console.error('Failed to load dashboard data:', failed.map(f => f.reason));
      }
    } catch (err) {
      setError('Không thể tải dữ liệu dashboard');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    
    // Refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'HEALTHY': return <CheckCircle className="w-5 h-5 text-emerald-400" />;
      case 'DEGRADED': return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      case 'DOWN': return <XCircle className="w-5 h-5 text-rose-400" />;
      case 'NOT_CONFIGURED': return <Wifi className="w-5 h-5 text-neutral-500" />;
      default: return <Loader2 className="w-5 h-5 text-neutral-500 animate-spin" />;
    }
  };

  const getWorkerHealthColor = (health: string) => {
    switch (health) {
      case 'ONLINE': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'DEGRADED': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'OFFLINE': return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'UNKNOWN': return 'text-neutral-500 bg-neutral-500/10 border-neutral-500/20';
      default: return 'text-neutral-500 bg-neutral-500/10 border-neutral-500/20';
    }
  };

  const getComponentIcon = (name: string) => {
    if (name.includes('Database')) return <Database className="w-5 h-5" />;
    if (name.includes('AI') || name.includes('Ollama')) return <Cpu className="w-5 h-5" />;
    if (name.includes('Storage')) return <HardDrive className="w-5 h-5" />;
    if (name.includes('Queue')) return <BarChart2 className="w-5 h-5" />;
    if (name.includes('Worker')) return <Server className="w-5 h-5" />;
    return <Server className="w-5 h-5" />;
  };

  if (loading && !stats) {
    return (
      <div className="space-y-8">
        <LiquidCard variant="clear" className="p-6">
          <div className="flex items-center gap-4">
            <Loader2 className="w-8 h-8 text-sky-400 animate-spin" />
            <div>
              <p className="text-lg font-semibold text-white">Đang tải dashboard quản trị...</p>
              <p className="text-sm text-neutral-400">Đang kết nối đến các dịch vụ backend</p>
            </div>
          </div>
        </LiquidCard>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="space-y-8">
        <LiquidCard variant="clear" className="p-6">
          <div className="flex items-center gap-4">
            <XCircle className="w-8 h-8 text-rose-400" />
            <div>
              <p className="text-lg font-semibold text-white">Không thể tải dashboard</p>
              <p className="text-sm text-neutral-400">{error}</p>
              <button 
                onClick={loadDashboardData}
                className="mt-3 px-4 py-2 rounded-lg apple-btn-primary text-sm"
              >
                <RefreshCw className="w-4 h-4 inline mr-1" />
                Thử lại
              </button>
            </div>
          </div>
        </LiquidCard>
      </div>
    );
  }

  return (
    <div className="space-y-8 md:space-y-12">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium tracking-wide text-neutral-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Bảng điều khiển quản trị</span>
            <span aria-hidden="true" className="text-neutral-600">·</span>
            <span className="text-sky-400">System Overview</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white apple-text-headline">
            Admin Dashboard
          </h1>
          <p className="text-sm text-neutral-400">
            Giám sát hệ thống, tài chính, AI review và worker status
          </p>
        </div>

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
          
          <button
            onClick={loadDashboardData}
            className="w-full sm:w-auto min-h-[44px] px-5 py-2.5 rounded-full apple-btn-secondary text-xs sm:text-sm flex items-center justify-center gap-2 active:scale-95 transition-all"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Làm mới</span>
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        {/* Current Balance */}
        <LiquidCard variant="clear" clarity="clear" className="flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-neutral-400">Số dư hiện tại</p>
              <p className="text-2xl sm:text-3xl font-bold text-white mt-1.5 font-tabular">
                {stats ? formatVND(stats.currentBalance) : '...'}
              </p>
            </div>
            <div className="w-9 h-9 rounded-full bg-white/[0.06] border border-white/10 flex items-center justify-center text-sky-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-6 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-neutral-400">
            <span>Số dư ban đầu: {stats ? formatVND(stats.openingBalance) : '...'}</span>
            <span className="text-emerald-400 font-medium">Tính từ sổ cái bất biến</span>
          </div>
        </LiquidCard>

        {/* Total Income */}
        <LiquidCard variant="clear" clarity="clear" className="flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-neutral-400">Tổng thu (CREDIT)</p>
              <p className="text-2xl sm:text-3xl font-bold text-emerald-400 mt-1.5 font-tabular">
                +{stats ? formatVND(stats.totalIncome) : '...'}
              </p>
            </div>
            <div className="w-9 h-9 rounded-full bg-white/[0.06] border border-white/10 flex items-center justify-center text-emerald-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-6 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-neutral-400">
            <span>{stats?.transactionCount || 0} giao dịch</span>
            <span className="text-emerald-400 font-medium">Đã xác thực</span>
          </div>
        </LiquidCard>

        {/* Total Expense */}
        <LiquidCard variant="clear" clarity="clear" className="flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-neutral-400">Tổng chi (DEBIT + REVERT)</p>
              <p className="text-2xl sm:text-3xl font-bold text-rose-400 mt-1.5 font-tabular">
                -{stats ? formatVND(stats.totalExpense) : '...'}
              </p>
            </div>
            <div className="w-9 h-9 rounded-full bg-white/[0.06] border border-white/10 flex items-center justify-center text-rose-400">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-6 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-neutral-400">
            <span>Chi quỹ & hoàn trả</span>
            <span className="text-rose-400 font-medium">Có log lưu</span>
          </div>
        </LiquidCard>

        {/* Pending Reviews */}
        <LiquidCard variant="clear" clarity="clear" className="flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-neutral-400">AI cần duyệt</p>
              <p className="text-2xl sm:text-3xl font-bold text-amber-400 mt-1.5 font-tabular">
                {stats?.pendingReviewCount || 0}
              </p>
            </div>
            <div className="w-9 h-9 rounded-full bg-white/[0.06] border border-white/10 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-6 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-neutral-400">
            <span>Đang xử lý: {stats?.processingReviewCount || 0}</span>
            <span className="text-amber-400 font-medium">Cần hành động</span>
          </div>
        </LiquidCard>
      </div>

      {/* System Health & Workers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* System Health */}
        <LiquidCard variant="clear" className="p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-white">Sức khỏe hệ thống</h3>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
              health?.overall === 'HEALTHY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              health?.overall === 'DEGRADED' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
              health?.overall === 'NOT_CONFIGURED' ? 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20' :
              'bg-rose-500/10 text-rose-400 border-rose-500/20'
            }`}>
              {health?.overall || 'UNKNOWN'}
            </span>
          </div>
          
          <div className="space-y-3">
            {health?.components.map((comp, idx) => (
              <div key={idx} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                <div className="w-9 h-9 rounded-full bg-white/[0.06] border border-white/10 flex items-center justify-center text-sky-400">
                  {getComponentIcon(comp.name)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{comp.name}</p>
                  <p className="text-xs text-neutral-400 truncate">{comp.details || 'Không có chi tiết'}</p>
                </div>
                <div className="flex items-center gap-2">
                  {getHealthIcon(comp.status)}
                  <span className={`text-xs font-medium ${comp.status === 'HEALTHY' ? 'text-emerald-400' : 
                    comp.status === 'DEGRADED' ? 'text-amber-400' : 
                    comp.status === 'DOWN' ? 'text-rose-400' : 'text-neutral-500'}`}>
                    {comp.status}
                  </span>
                  {comp.latencyMs && (
                    <span className="text-[10px] text-neutral-500 px-2 py-0.5 rounded bg-white/[0.05]">
                      {comp.latencyMs}ms
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </LiquidCard>

        {/* Worker Status */}
        <LiquidCard variant="clear" className="p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-white">Worker Status</h3>
            <span className="text-xs text-neutral-400">
              {workers.filter(w => w.health === 'ONLINE').length} / {workers.length} online
            </span>
          </div>
          
          {workers.length === 0 ? (
            <div className="text-center py-8">
              <Server className="w-12 h-12 text-neutral-600 mx-auto mb-3" />
              <p className="text-sm font-medium text-neutral-300">Không có worker nào được đăng ký</p>
              <p className="text-xs text-neutral-500 mt-1">Khởi động worker để xử lý tin nhắn AI</p>
            </div>
          ) : (
            <div className="space-y-2">
              {workers.map((worker) => (
                <div 
                  key={worker.workerId} 
                  className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]"
                >
                  <div className="w-9 h-9 rounded-full bg-white/[0.06] border border-white/10 flex items-center justify-center text-sky-400">
                    <Server className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{worker.workerId}</p>
                    <div className="flex items-center gap-2 text-xs text-neutral-400 mt-0.5">
                      {worker.modelName && <span>{worker.modelName}</span>}
                      {worker.lastHeartbeat && (
                        <>
                          <span aria-hidden="true">·</span>
                          <span>Heartbeat: {Math.round(worker.secondsSinceHeartbeat || 0)}s trước</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getWorkerHealthColor(worker.health)}`}>
                      {worker.health}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </LiquidCard>
      </div>

      {/* Queue Status & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Queue Status */}
        <LiquidCard variant="clear" className="p-4 sm:p-6">
          <h3 className="text-lg font-bold text-white mb-4">Hàng đợi xử lý</h3>
          
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] text-center">
              <p className="text-2xl font-bold text-neutral-300 font-tabular">{queueStatus?.pending || 0}</p>
              <p className="text-xs text-neutral-400 mt-1">Chờ xử lý</p>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] text-center">
              <p className="text-2xl font-bold text-sky-400 font-tabular">{queueStatus?.processing || 0}</p>
              <p className="text-xs text-neutral-400 mt-1">Đang xử lý</p>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] text-center">
              <p className="text-2xl font-bold text-amber-400 font-tabular">{queueStatus?.awaitingReview || 0}</p>
              <p className="text-xs text-neutral-400 mt-1">Cần duyệt</p>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] text-center">
              <p className="text-2xl font-bold text-emerald-400 font-tabular">{queueStatus?.postedToday || 0}</p>
              <p className="text-xs text-neutral-400 mt-1">Đã đăng hôm nay</p>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] text-center">
              <p className="text-2xl font-bold text-rose-400 font-tabular">{queueStatus?.failedToday || 0}</p>
              <p className="text-xs text-neutral-400 mt-1">Thất bại hôm nay</p>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] text-center">
              <p className="text-2xl font-bold text-neutral-400 font-tabular">{queueStatus?.recalledToday || 0}</p>
              <p className="text-xs text-neutral-400 mt-1">Đã thu hồi hôm nay</p>
            </div>
          </div>

          {queueStatus?.oldestPendingAgeSeconds && (
            <div className="mt-4 pt-4 border-t border-white/[0.08]">
              <p className="text-xs text-neutral-400">
                Cũ nhất chờ xử lý: {Math.floor((queueStatus.oldestPendingAgeSeconds || 0) / 60)} phút trước
              </p>
            </div>
          )}
        </LiquidCard>

        {/* Quick Navigation */}
        <LiquidCard variant="clear" className="p-4 sm:p-6">
          <h3 className="text-lg font-bold text-white mb-4">Truy cập nhanh</h3>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              onClick={() => setCurrentTab('admin-review')}
              className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-sky-500/30 hover:bg-white/[0.08] transition-all text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-medium text-white group-hover:text-sky-300 transition-colors">AI Review Queue</p>
                  <p className="text-xs text-neutral-400">{stats?.pendingReviewCount || 0} cần duyệt</p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-neutral-400 group-hover:text-white transition-colors ml-auto" />
            </button>

            <button
              onClick={() => setCurrentTab('admin-ledger')}
              className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-emerald-500/30 hover:bg-white/[0.08] transition-all text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <BarChart2 className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-medium text-white group-hover:text-sky-300 transition-colors">Quản lý sổ cái</p>
                  <p className="text-xs text-neutral-400">{stats?.transactionCount || 0} giao dịch</p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-neutral-400 group-hover:text-white transition-colors ml-auto" />
            </button>

            <button
              onClick={() => setCurrentTab('admin-audit')}
              className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-neutral-500/30 hover:bg-white/[0.08] transition-all text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-neutral-500/10 border border-neutral-500/20 flex items-center justify-center text-neutral-400">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-medium text-white group-hover:text-sky-300 transition-colors">Nhật ký kiểm toán</p>
                  <p className="text-xs text-neutral-400">Lịch sử bất biến</p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-neutral-400 group-hover:text-white transition-colors ml-auto" />
            </button>

            <button
              onClick={() => setCurrentTab('admin-system')}
              className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-sky-500/30 hover:bg-white/[0.08] transition-all text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-medium text-white group-hover:text-sky-300 transition-colors">Giám sát hệ thống</p>
                  <p className="text-xs text-neutral-400">Worker, Queue, Health</p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-neutral-400 group-hover:text-white transition-colors ml-auto" />
            </button>
          </div>
        </LiquidCard>
      </div>
    </div>
  );
};