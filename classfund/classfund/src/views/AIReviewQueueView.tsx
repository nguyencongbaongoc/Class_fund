import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND } from '../data/mockDatabase';
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Eye, 
  Loader2, 
  ChevronLeft,
  ChevronRight,
  ImageIcon,
  FileText,
  AlertCircle,
  CheckCircle2,
  XCircle as XCircleIcon,
  Clock,
  ShieldCheck,
  MoreVertical
} from 'lucide-react';
import { adminApi, ReviewQueueItem, ReviewDetail, ReviewResponse } from '../lib/adminApi';

export const AIReviewQueueView: React.FC = () => {
  const { currentUser, addToast, setCurrentTab } = useApp();

  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedExtraction, setSelectedExtraction] = useState<ReviewDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showImageModal, setShowImageModal] = useState<string | null>(null);

  const loadQueue = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getReviewQueue({ status: 'NEEDS_REVIEW', limit: 50 });
      setQueue(data);
    } catch (err: any) {
      setError(err.message || 'Không thể tải hàng đợi duyệt');
      addToast({ type: 'error', title: 'Lỗi', description: err.message });
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (extractionId: string) => {
    try {
      setDetailLoading(true);
      const data = await adminApi.getReviewDetail(extractionId);
      setSelectedExtraction(data);
    } catch (err: any) {
      addToast({ type: 'error', title: 'Lỗi', description: 'Không thể tải chi tiết' });
    } finally {
      setDetailLoading(false);
    }
  };

  const handleApprove = async (extractionId: string) => {
    if (!window.confirm('Xác nhận duyệt biên lai này? Giao dịch sẽ được ghi vào sổ cái.')) return;
    
    try {
      setActionLoading(extractionId);
      const result = await adminApi.approveExtraction(extractionId, true);
      
      if (result.status === 'VERIFIED') {
        addToast({ 
          type: 'success', 
          title: 'Đã duyệt', 
          description: `Đã ghi giao dịch ${result.transactionId?.slice(0, 8)} vào sổ cái` 
        });
      } else if (result.status === 'DUPLICATE') {
        addToast({ 
          type: 'warning', 
          title: 'Trùng lặp', 
          description: 'Giao dịch này đã tồn tại trong sổ cái' 
        });
      }
      
      setSelectedExtraction(null);
      loadQueue();
    } catch (err: any) {
      addToast({ type: 'error', title: 'Lỗi duyệt', description: err.message || 'Không thể duyệt' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (extractionId: string) => {
    const reason = window.prompt('Lý do từ chối:');
    if (!reason || !reason.trim()) return;
    
    try {
      setActionLoading(extractionId);
      const result = await adminApi.rejectExtraction(extractionId, reason.trim());
      
      addToast({ 
        type: 'success', 
        title: 'Đã từ chối', 
        description: `Biên lai đã bị đánh dấu REJECTED: ${reason}` 
      });
      
      setSelectedExtraction(null);
      loadQueue();
    } catch (err: any) {
      addToast({ type: 'error', title: 'Lỗi từ chối', description: err.message || 'Không thể từ chối' });
    } finally {
      setActionLoading(null);
    }
  };

  const getConfidenceColor = (confidence: number | null) => {
    if (confidence === null) return 'text-neutral-400';
    if (confidence >= 0.95) return 'text-emerald-400';
    if (confidence >= 0.85) return 'text-amber-400';
    return 'text-rose-400';
  };

  const getConfidenceLabel = (confidence: number | null) => {
    if (confidence === null) return 'N/A';
    if (confidence >= 0.95) return 'Rất cao';
    if (confidence >= 0.85) return 'Cao';
    if (confidence >= 0.7) return 'Trung bình';
    return 'Thấp';
  };

  useEffect(() => {
    loadQueue();
  }, []);

  return (
    <div className="space-y-6 md:space-y-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium tracking-wide text-neutral-400">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>Hàng đợi duyệt AI</span>
            <span aria-hidden="true" className="text-neutral-600">·</span>
            <span>Cần hành động thủ quỹ</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white apple-text-headline">
            AI Review Queue
          </h1>
          <p className="text-sm text-neutral-400">
            {queue.length} biên lai chờ duyệt. Mỗi biên lai cần được kiểm tra trước khi ghi sổ.
          </p>
        </div>

        <button
          onClick={loadQueue}
          disabled={loading}
          className="flex-1 sm:flex-none min-h-[44px] px-5 py-2.5 rounded-full apple-btn-secondary text-xs sm:text-sm flex items-center justify-center gap-2 active:scale-95 transition-all"
        >
          <Loader2 className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Làm mới</span>
        </button>
      </div>

      {/* Queue Table */}
      <LiquidCard variant="clear" className="p-0 overflow-hidden">
        {loading && queue.length === 0 ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-sky-400 animate-spin mx-auto mb-3" />
            <p className="text-sm font-medium text-neutral-300">Đang tải hàng đợi...</p>
          </div>
        ) : error && queue.length === 0 ? (
          <div className="p-12 text-center">
            <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-white mb-1">Không thể tải dữ liệu</p>
            <p className="text-xs text-neutral-400 mb-4">{error}</p>
            <button onClick={loadQueue} className="px-4 py-2 rounded-lg apple-btn-primary text-sm">
              Thử lại
            </button>
          </div>
        ) : queue.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-white mb-1">Không có biên lai cần duyệt</p>
            <p className="text-xs text-neutral-400">Tất cả biên lai đã được xử lý</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/[0.08] text-[11px] font-semibold text-neutral-400 uppercase tracking-widest bg-white/[0.02]">
                  <th className="py-3 px-4 sm:px-6">Thời gian</th>
                  <th className="py-3 px-4">Mã GD</th>
                  <th className="py-3 px-4">Người gửi</th>
                  <th className="py-3 px-4">Số tiền</th>
                  <th className="py-3 px-4">Ngân hàng</th>
                  <th className="py-3 px-4 text-center">Độ tin cậy</th>
                  <th className="py-3 px-4 text-center">Trạng thái</th>
                  <th className="py-3 px-4 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] text-xs sm:text-sm">
                {queue.map((item) => (
                  <tr
                    key={item.extractionId}
                    onClick={() => loadDetail(item.extractionId)}
                    className="hover:bg-white/[0.05] transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-4 sm:px-6 text-neutral-400 font-tabular whitespace-nowrap">
                      {new Date(item.createdAt).toLocaleString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-medium text-neutral-200 whitespace-nowrap">
                      {item.transactionCode || '—'}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-white truncate max-w-xs">
                      {item.senderName || '—'}
                    </td>
                    <td className="py-3.5 px-4 text-right font-bold font-tabular whitespace-nowrap text-emerald-400">
                      {item.amount ? formatVND(item.amount) : '—'}
                    </td>
                    <td className="py-3.5 px-4 text-neutral-300 truncate max-w-xs">
                      {item.bankName || '—'}
                    </td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${getConfidenceColor(item.confidence)}`}>
                        {item.confidence ? `${Math.round(item.confidence * 100)}%` : 'N/A'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border bg-amber-500/10 text-amber-400 border-amber-500/20">
                        Cần duyệt
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={(e) => { e.stopPropagation(); loadDetail(item.extractionId); }}
                        className="text-xs font-medium text-sky-400 hover:text-sky-300 hover:underline mr-3"
                      >
                        Chi tiết
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </LiquidCard>

      {/* Detail Modal */}
      {selectedExtraction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={() => setSelectedExtraction(null)}>
          <div className="w-full max-w-4xl max-h-[90vh] overflow-hidden apple-frosted-glass rounded-2xl border border-white/10 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 sm:p-6 border-b border-white/[0.08]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm text-neutral-400">Mã trích xuất</p>
                  <p className="font-mono font-bold text-white">{selectedExtraction.extractionId.slice(0, 12)}...</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedExtraction(null)}
                className="p-2 rounded-full hover:bg-white/[0.1] transition-colors text-neutral-400 hover:text-white"
              >
                <XCircleIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4 sm:p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left: Extracted Fields */}
                <div className="space-y-4">
                  <h3 className="text-lg font-bold text-white border-b border-white/[0.08] pb-2">Thông tin trích xuất</h3>
                  
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-xs text-neutral-400">Mã giao dịch</p>
                        <p className="font-mono font-medium text-white">{selectedExtraction.transactionCode || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-400">Số tiền</p>
                        <p className="font-bold text-emerald-400 font-tabular text-lg">
                          {selectedExtraction.amount ? formatVND(selectedExtraction.amount) : '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-400">Người gửi</p>
                        <p className="font-medium text-white">{selectedExtraction.senderName || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-400">Ngân hàng</p>
                        <p className="font-medium text-white">{selectedExtraction.bankName || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-400">Thời gian GD</p>
                        <p className="font-medium text-white">
                          {selectedExtraction.transactionTime ? new Date(selectedExtraction.transactionTime).toLocaleString('vi-VN') : '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-400">Độ tin cậy</p>
                        <p className={`font-bold text-lg ${getConfidenceColor(selectedExtraction.confidence)}`}>
                          {selectedExtraction.confidence ? `${Math.round(selectedExtraction.confidence * 100)}%` : 'N/A'}
                          <span className="text-xs font-normal text-neutral-400 ml-1">({getConfidenceLabel(selectedExtraction.confidence)})</span>
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-400">Phương pháp</p>
                        <p className="font-medium text-white">{selectedExtraction.extractionMethod || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-400">Tiền tệ</p>
                        <p className="font-medium text-white">{selectedExtraction.currency || 'VND'}</p>
                      </div>
                    </div>
                  </div>

                  {/* Field Confidences */}
                  {selectedExtraction.fieldConfidences && Object.keys(selectedExtraction.fieldConfidences).length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-neutral-300 mb-2">Độ tin cậy từng trường</h4>
                      <div className="space-y-2">
                        {Object.entries(selectedExtraction.fieldConfidences).map(([field, conf]) => (
                          <div key={field} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.03]">
                            <span className="text-xs text-neutral-300 capitalize">{field.replace(/_/g, ' ')}</span>
                            <div className="flex items-center gap-2">
                              <div className="w-24 h-2 bg-white/[0.1] rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-gradient-to-r from-rose-500 via-amber-500 to-emerald-500 transition-all duration-300"
                                  style={{ width: `${conf * 100}%` }}
                                />
                              </div>
                              <span className={`text-xs font-mono ${getConfidenceColor(conf)}`}>{Math.round(conf * 100)}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Raw OCR */}
                  {selectedExtraction.rawOcr && (
                    <div>
                      <h4 className="text-sm font-medium text-neutral-300 mb-2">Raw OCR Text</h4>
                      <pre className="p-3 rounded-lg bg-black/30 border border-white/[0.05] text-[10px] text-neutral-300 overflow-x-auto max-h-40 whitespace-pre-wrap font-mono">
                        {selectedExtraction.rawOcr}
                      </pre>
                    </div>
                  )}
                </div>

                {/* Right: Upload Info & Image */}
                <div className="space-y-4">
                  {selectedExtraction.upload && (
                    <div className="space-y-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <h4 className="font-medium text-white flex items-center gap-2">
                        <FileText className="w-4 h-4 text-sky-400" />
                        File gốc
                      </h4>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div><span className="text-neutral-400">Tên file: </span><span className="text-white truncate">{selectedExtraction.upload.originalFilename}</span></div>
                        <div><span className="text-neutral-400">Người nộp: </span><span className="text-white">{selectedExtraction.upload.uploaderName}</span></div>
                        <div className="col-span-2"><span className="text-neutral-400">Thời gian: </span><span className="text-white">{new Date(selectedExtraction.upload.createdAt).toLocaleString('vi-VN')}</span></div>
                      </div>
                      <button
                        onClick={() => setShowImageModal(adminApi.getImageUrl(selectedExtraction.upload!.id))}
                        className="mt-2 px-3 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs hover:bg-sky-500/20 transition-colors flex items-center gap-1"
                      >
                        <ImageIcon className="w-3 h-3" />
                        Xem ảnh gốc
                      </button>
                    </div>
                  )}

                  {selectedExtraction.message && (
                    <div className="space-y-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <h4 className="font-medium text-white flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        Tin nhắn liên quan
                      </h4>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div><span className="text-neutral-400">Mã công khai: </span><span className="font-mono text-white">{selectedExtraction.message.publicCode || '—'}</span></div>
                        <div><span className="text-neutral-400">Người gửi: </span><span className="text-white">{selectedExtraction.message.senderName}</span></div>
                        <div className="col-span-2"><span className="text-neutral-400">Nội dung: </span><span className="text-white truncate">{selectedExtraction.message.content}</span></div>
                      </div>
                    </div>
                  )}

                  {/* Warnings */}
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-neutral-300">Cảnh báo & Kiểm tra</h4>
                    
                    {selectedExtraction.confidence !== null && selectedExtraction.confidence < 0.9 && (
                      <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-amber-300">Low confidence</p>
                          <p className="text-xs text-amber-400 mt-0.5">Confidence {Math.round((selectedExtraction.confidence || 0) * 100)}% is less than 90%. Review carefully before approving.</p>
                        </div>
                      </div>
                    )}

                    {!selectedExtraction.transactionCode && (
                      <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-rose-300">Missing transaction code</p>
                          <p className="text-xs text-rose-400 mt-0.5">Cannot check for duplicates. Manual verification required.</p>
                        </div>
                      </div>
                    )}

                    {selectedExtraction.confidence !== null && selectedExtraction.confidence >= 0.95 && (
                      <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-emerald-300">High confidence</p>
                          <p className="text-xs text-emerald-400 mt-0.5">Confidence {Math.round((selectedExtraction.confidence || 0) * 100)}% is greater than or equal to 95%. Auto-pass threshold.</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-6 pt-6 border-t border-white/[0.08] flex flex-col sm:flex-row gap-3 justify-end">
                <button
                  onClick={() => handleReject(selectedExtraction.extractionId)}
                  disabled={actionLoading === selectedExtraction.extractionId || detailLoading}
                  className="px-6 py-2.5 rounded-full bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 font-medium text-sm flex items-center justify-center gap-1.5 border border-rose-500/25 active:scale-95 transition-all disabled:opacity-50"
                >
                  {actionLoading === selectedExtraction.extractionId ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircleIcon className="w-4 h-4" />}
                  <span>Từ chối</span>
                </button>
                <button
                  onClick={() => handleApprove(selectedExtraction.extractionId)}
                  disabled={actionLoading === selectedExtraction.extractionId || detailLoading}
                  className="px-6 py-2.5 rounded-full apple-btn-primary font-medium text-sm flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/25 active:scale-95 transition-all disabled:opacity-50"
                >
                  {actionLoading === selectedExtraction.extractionId ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                  <span>Duyệt & Ghi sổ</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Image Modal */}
      {showImageModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90" onClick={() => setShowImageModal(null)}>
          <img 
            src={showImageModal} 
            alt="Receipt image" 
            className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
};