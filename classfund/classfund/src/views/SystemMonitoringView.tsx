import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { 
  Server, 
  Database, 
  Cpu, 
  HardDrive, 
  Wifi, 
  Loader2, 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  RefreshCw,
  BarChart2,
  Clock,
  Zap,
  Activity,
  Heart,
  TrendingUp,
  ExternalLink,
  MoreVertical,
  RotateCcw
} from 'lucide-react';
import { adminApi, WorkerStatus, SystemHealth, QueueStatus, ComponentHealth } from '../lib/adminApi';

export const SystemMonitoringView: React.FC = () => {
  const { currentUser, addToast } = useApp();

  const [workers, setWorkers] = useState<WorkerStatus[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [workersRes, healthRes, queueRes] = await Promise.allSettled([
        adminApi.getWorkers(),
        adminApi.getHealth(),
        adminApi.getQueueStatus(),
      ]);

      if (workersRes.status === 'fulfilled') setWorkers(workersRes.value);
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value);
      if (queueRes.status === 'fulfilled') setQueueStatus(queueRes.value);

      const failed = [workersRes, healthRes, queueRes].filter(r => r.status === 'rejected');
      if (failed.length > 0) {
        console.error('Failed to load monitoring data:', failed.map(f => f.reason));
      }
      
      setLastRefresh(new Date());
    } catch (err) {
      setError('Không thể tải dữ liệu giám sát');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30 seconds
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

  const formatUptime = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  return (
    <div className="space-y-6 md:space-y-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium tracking-wide text-neutral-400">
            <Server className="w-4 h-4 text-sky-400" />
            <span>Giám sát hệ thống</span>
            <span aria-hidden="true" className="text-neutral-600">·</span>
            <span>Worker, Queue, Health Checks</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white apple-text-headline">
            System Monitoring
          </h1>
          <p className="text-sm text-neutral-400">
            Theo dõi sức khỏe các thành phần hệ thống và trạng thái worker
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex-1 sm:flex-none min-h-[44px] px-5 py-2.5 rounded-full apple-btn-primary font-medium text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-sky-600/25 active:scale-95 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Làm mới</span>
          </button>
        </div>
      </div>

      {/* Overall System Health */}
      <LiquidCard variant="clear" className="p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-sky-400" />
            Sức khỏe tổng thể hệ thống
          </h3>
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${
              health?.overall === 'HEALTHY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              health?.overall === 'DEGRADED' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
              health?.overall === 'NOT_CONFIGURED' ? 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20' :
              health?.overall === 'DOWN' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
              'bg-neutral-500/10 text-neutral-400 border-neutral-500/20'
            }`}>
              {health?.overall || 'LOADING...'}
            </span>
            {lastRefresh && (
              <span className="text-xs text-neutral-400">
                Cập nhật: {lastRefresh.toLocaleTimeString('vi-VN')}
              </span>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {health?.components.map((comp, idx) => (
            <div 
              key={idx} 
              className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-white/[0.15] transition-colors"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-white/[0.06] border border-white/10 flex items-center justify-center text-sky-400 flex-shrink-0">
                  {getComponentIcon(comp.name)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-white truncate">{comp.name}</p>
                  <p className="text-xs text-neutral-400 truncate mt-0.5">{comp.details || 'Không có chi tiết'}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className="flex items-center gap-2">
                    {getHealthIcon(comp.status)}
                    <span className={`text-sm font-medium ${comp.status === 'HEALTHY' ? 'text-emerald-400' : 
                      comp.status === 'DEGRADED' ? 'text-amber-400' : 
                      comp.status === 'DOWN' ? 'text-rose-400' : 'text-neutral-500'}`}>
                      {comp.status}
                    </span>
                  </div>
                  {comp.latencyMs && (
                    <span className="text-[10px] text-neutral-500 px-2 py-0.5 rounded bg-white/[0.05] font-mono">
                      {comp.latencyMs}ms
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </LiquidCard>

      {/* Worker Status & Queue Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Worker Status */}
        <LiquidCard variant="clear" className="p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-sky-400" />
              Worker Pool
            </h3>
            <div className="flex items-center gap-3">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                workers.filter(w => w.health === 'ONLINE').length > 0 
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 border' 
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20 border'
              }`}>
                {workers.filter(w => w.health === 'ONLINE').length} / {workers.length} Online
              </span>
            </div>
          </div>
          
          {workers.length === 0 ? (
            <div className="text-center py-12">
              <Server className="w-16 h-16 text-neutral-600 mx-auto mb-4" />
              <p className="text-sm font-medium text-neutral-300 mb-1">Không có worker nào được đăng ký</p>
              <p className="text-xs text-neutral-500">Khởi động worker service để xử lý tin nhắn AI</p>
              <div className="mt-4 p-3 rounded-lg bg-white/[0.03] border border-white/[0.05] text-left max-w-xs mx-auto text-xs">
                <p className="font-medium text-white mb-2">Cách khởi động worker:</p>
                <code className="text-neutral-400 font-mono">docker run -e DATABASE_URL=... -e WORKER_ID=worker-1 class-fund-worker</code>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {workers.map((worker) => (
                <div 
                  key={worker.workerId} 
                  className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-white/[0.1] transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4 flex-1">
                      <div className="w-12 h-12 rounded-xl bg-white/[0.06] border border-white/10 flex items-center justify-center text-sky-400 flex-shrink-0">
                        <Server className="w-5 h-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-3">
                          <p className="font-mono font-medium text-white">{worker.workerId}</p>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getWorkerHealthColor(worker.health)}`}>
                            {worker.health}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-4 mt-2 text-xs text-neutral-400">
                          {worker.modelName && (
                            <span className="flex items-center gap-1">
                              <Zap className="w-3 h-3" />
                              {worker.modelName}
                            </span>
                          )}
                          {worker.lastHeartbeat && (
                            <span className="flex items-center gap-1">
                              <Heart className="w-3 h-3" />
                              Heartbeat: {formatUptime(worker.secondsSinceHeartbeat)}
                            </span>
                          )}
                          {worker.currentJobId && (
                            <span className="flex items-center gap-1 text-amber-400">
                              <Activity className="w-3 h-3" />
                              Processing: {worker.currentJobId.slice(0, 12)}...
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3 flex-shrink-0">
                      {worker.lastProcessedAt && (
                        <span className="text-[10px] text-neutral-500 px-2 py-1 rounded bg-white/[0.05] font-mono whitespace-nowrap">
                          Last: {new Date(worker.lastProcessedAt).toLocaleTimeString('vi-VN')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </LiquidCard>

        {/* Queue Status */}
        <LiquidCard variant="clear" className="p-4 sm:p-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
            <BarChart2 className="w-5 h-5 text-sky-400" />
            Hàng đợi xử lý tin nhắn
          </h3>
          
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            <MetricCard 
              label="Chờ xử lý" 
              value={queueStatus?.pending || 0} 
              icon={<Clock className="w-5 h-5" />} 
              color="neutral"
            />
            <MetricCard 
              label="Đang xử lý" 
              value={queueStatus?.processing || 0} 
              icon={<Loader2 className="w-5 h-5 animate-spin" />} 
              color="sky"
            />
            <MetricCard 
              label="Cần duyệt" 
              value={queueStatus?.awaitingReview || 0} 
              icon={<AlertTriangle className="w-5 h-5" />} 
              color="amber"
            />
            <MetricCard 
              label="Đã đăng hôm nay" 
              value={queueStatus?.postedToday || 0} 
              icon={<CheckCircle className="w-5 h-5" />} 
              color="emerald"
            />
            <MetricCard 
              label="Thất bại hôm nay" 
              value={queueStatus?.failedToday || 0} 
              icon={<XCircle className="w-5 h-5" />} 
              color="rose"
            />
            <MetricCard 
              label="Thu hồi hôm nay" 
              value={queueStatus?.recalledToday || 0} 
              icon={<RotateCcw className="w-5 h-5" />} 
              color="neutral"
            />
          </div>

          <div className="space-y-3 p-3 rounded-lg bg-white/[0.03] border border-white/[0.05]">
            {queueStatus?.oldestPendingAgeSeconds !== null && queueStatus?.oldestPendingAgeSeconds !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-300">Cũ nhất chờ xử lý</span>
                <span className="font-mono text-lg text-amber-400">
                  {Math.floor((queueStatus.oldestPendingAgeSeconds || 0) / 60)} phút { (queueStatus.oldestPendingAgeSeconds || 0) % 60 } giây
                </span>
              </div>
            )}
            {queueStatus?.avgProcessingTimeSeconds !== null && queueStatus?.avgProcessingTimeSeconds !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-300">Thời gian xử lý TB</span>
                <span className="font-mono text-lg text-sky-400">
                  {queueStatus.avgProcessingTimeSeconds < 60 
                    ? `${Math.round(queueStatus.avgProcessingTimeSeconds)}s` 
                    : `${Math.round(queueStatus.avgProcessingTimeSeconds / 60)}m ${Math.round(queueStatus.avgProcessingTimeSeconds % 60)}s`}
                </span>
              </div>
            )}
          </div>
        </LiquidCard>
      </div>

      {/* System Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Queue Details */}
        <LiquidCard variant="clear" className="p-4 sm:p-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
            <Database className="w-5 h-5 text-sky-400" />
            Chi tiết hàng đợi
          </h3>
          
          <div className="space-y-2 text-sm">
            <DetailRow label="Tổng tin nhắn chờ" value={queueStatus?.pending || 0} />
            <DetailRow label="Đang được worker xử lý" value={queueStatus?.processing || 0} />
            <DetailRow label="Chờ duyệt thủ công" value={queueStatus?.awaitingReview || 0} />
            <DetailRow label="Đã đăng thành công hôm nay" value={queueStatus?.postedToday || 0} color="emerald" />
            <DetailRow label="Thất bại hôm nay" value={queueStatus?.failedToday || 0} color="rose" />
            <DetailRow label="Đã thu hồi hôm nay" value={queueStatus?.recalledToday || 0} color="amber" />
          </div>
        </LiquidCard>

        {/* Quick Actions */}
        <LiquidCard variant="clear" className="p-4 sm:p-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
            <ExternalLink className="w-5 h-5 text-sky-400" />
            Truy cập nhanh
          </h3>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <a 
              href="/docs" 
              target="_blank" 
              rel="noopener noreferrer"
              className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-sky-500/30 hover:bg-white/[0.08] transition-all text-left group flex items-center gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                <ExternalLink className="w-5 h-5" />
              </div>
              <div>
                <p className="font-medium text-white group-hover:text-sky-300 transition-colors">API Documentation</p>
                <p className="text-xs text-neutral-400">Swagger UI / ReDoc</p>
              </div>
            </a>

            <button
              onClick={loadData}
              disabled={loading}
              className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-emerald-500/30 hover:bg-white/[0.08] transition-all text-left group flex items-center gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <RefreshCw className="w-5 h-5" />
              </div>
              <div>
                <p className="font-medium text-white group-hover:text-sky-300 transition-colors">Làm mới tất cả</p>
                <p className="text-xs text-neutral-400">Cập nhật dữ liệu giám sát</p>
              </div>
            </button>
          </div>
        </LiquidCard>
      </div>
    </div>
  );
};

const MetricCard: React.FC<{ 
  label: string; 
  value: number; 
  icon: React.ReactNode; 
  color: 'neutral' | 'sky' | 'amber' | 'emerald' | 'rose' 
}> = ({ label, value, icon, color }) => {
  const colors = {
    neutral: 'text-neutral-300',
    sky: 'text-sky-400',
    amber: 'text-amber-400',
    emerald: 'text-emerald-400',
    rose: 'text-rose-400',
  };
  
  const bgColors = {
    neutral: 'bg-neutral-500/10 border-neutral-500/20',
    sky: 'bg-sky-500/10 border-sky-500/20',
    amber: 'bg-amber-500/10 border-amber-500/20',
    emerald: 'bg-emerald-500/10 border-emerald-500/20',
    rose: 'bg-rose-500/10 border-rose-500/20',
  };

  return (
    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] text-center">
      <div className={`w-10 h-10 rounded-full ${bgColors[color]} flex items-center justify-center mx-auto mb-2`}>
        {icon}
      </div>
      <p className="text-2xl font-bold font-tabular" style={{ color: colors[color] }}>{value}</p>
      <p className="text-xs text-neutral-400 mt-1">{label}</p>
    </div>
  );
};

const DetailRow: React.FC<{ 
  label: string; 
  value: number; 
  color?: 'neutral' | 'sky' | 'amber' | 'emerald' | 'rose' 
}> = ({ label, value, color = 'neutral' }) => {
  const colors = {
    neutral: 'text-neutral-300',
    sky: 'text-sky-400',
    amber: 'text-amber-400',
    emerald: 'text-emerald-400',
    rose: 'text-rose-400',
  };

  return (
    <div className="flex items-center justify-between p-2 rounded-lg bg-white/[0.03] border border-white/[0.05]">
      <span className="text-neutral-400">{label}</span>
      <span className="font-mono font-medium" style={{ color: colors[color] }}>{value}</span>
    </div>
  );
};