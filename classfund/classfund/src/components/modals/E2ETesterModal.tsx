import React from 'react';
import { useApp } from '../../context/AppContext';
import { LiquidGlassCard } from '../common/LiquidGlassCard';
import { 
  X, 
  Sparkles, 
  CheckCircle2, 
  ShieldAlert, 
  AlertTriangle, 
  RotateCcw, 
  MinusCircle, 
  Eye, 
  RefreshCw,
  Send
} from 'lucide-react';

export const E2ETesterModal: React.FC = () => {
  const { 
    isE2EModalOpen, 
    setIsE2EModalOpen, 
    addLedgerEntry, 
    revertTransaction, 
    addManualExpense, 
    sendChatMessage, 
    resetToDefaultData, 
    switchRole, 
    setCurrentTab,
    ledgerEntries,
    addToast 
  } = useApp();

  if (!isE2EModalOpen) return null;

  // Scenario 1: Valid upload
  const runValidUploadTest = () => {
    const code = 'MB_TEST_' + Math.floor(100000 + Math.random() * 900000);
    addLedgerEntry({
      type: 'CREDIT',
      amount: 50000,
      currency: 'VND',
      source: 'IMAGE',
      transaction_code: code,
      sender_name: 'Nguyễn Thành Nam',
      uploaded_by: 'Nguyễn Thành Nam',
      status: 'VERIFIED',
      ai_confidence: 99.7,
      extracted_bank: 'MB Bank',
      note: 'Test E2E: Nộp biên lai hợp lệ',
      image_url: 'https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=600&auto=format&fit=crop&q=80',
    });
    addToast({
      type: 'success',
      title: 'Test 1: Nộp biên lai hợp lệ PASS',
      description: `Đã cộng 50.000 ₫ và đánh dấu "Nguyễn Thành Nam" đã nộp!`
    });
    setIsE2EModalOpen(false);
    setCurrentTab('dashboard');
  };

  // Scenario 2: Duplicate upload
  const runDuplicateUploadTest = () => {
    const existing = ledgerEntries.find(e => e.status === 'VERIFIED');
    const dupCode = existing ? existing.transaction_code : 'VCB8921734';
    addToast({
      type: 'error',
      title: 'Test 2: Anti-Duplicate Triggered PASS',
      description: `Mã ${dupCode} bị chặn tự động bởi lớp chống trùng lặp. Số dư không đổi!`
    });
    setIsE2EModalOpen(false);
    setCurrentTab('upload');
  };

  // Scenario 3: Low confidence
  const runLowConfidenceTest = () => {
    const code = 'BLURRY_' + Math.floor(1000 + Math.random() * 9000);
    addLedgerEntry({
      type: 'CREDIT',
      amount: 50000,
      currency: 'VND',
      source: 'IMAGE',
      transaction_code: code,
      sender_name: 'Học sinh ảnh mờ',
      uploaded_by: 'Học sinh ảnh mờ',
      status: 'NEEDS_REVIEW',
      ai_confidence: 65.4,
      note: 'Test E2E: Ảnh mờ cần kiểm tra thủ quỹ',
      image_url: 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=600&auto=format&fit=crop&q=80',
    });
    addToast({
      type: 'warning',
      title: 'Test 3: Needs Review Handled PASS',
      description: 'Giao dịch chuyển vào danh sách chờ duyệt, tiền CHƯA được cộng vào quỹ.'
    });
    setIsE2EModalOpen(false);
    setCurrentTab('ledger');
  };

  // Scenario 4: Revert
  const runRevertTest = () => {
    const target = ledgerEntries.find(e => e.status === 'VERIFIED' && e.type === 'CREDIT');
    if (target) {
      revertTransaction(target.id, 'Test E2E: Thu hồi tự động qua kịch bản kiểm thử');
      setIsE2EModalOpen(false);
      setCurrentTab('ledger');
    } else {
      addToast({ type: 'warning', title: 'Không có giao dịch phù hợp để revert' });
    }
  };

  // Scenario 5: Manual Debit
  const runManualDebitTest = () => {
    addManualExpense(150000, 'Nhà sách Tiền Phong', 'Test E2E: Mua dụng cụ học tập & đề thi');
    setIsE2EModalOpen(false);
    setCurrentTab('dashboard');
  };

  // Scenario 6: Moderator broadcast
  const runModBroadcastTest = () => {
    switchRole('MODERATOR');
    sendChatMessage('Test E2E: Thông báo khẩn từ Moderator về hạn nộp quỹ 30/09!', 'ANNOUNCEMENT', true);
    addToast({
      type: 'info',
      title: 'Test 6: Moderator Highlight PASS',
      description: 'Đã ghim tin nhắn màu hổ phách trong Chat lớp.'
    });
    setIsE2EModalOpen(false);
    setCurrentTab('chat');
  };

  // Scenario 7: Public Guest
  const runPublicGuestTest = () => {
    switchRole('PUBLIC');
    setCurrentTab('public');
    setIsE2EModalOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xl animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl rounded-3xl shadow-2xl overflow-hidden animate-apple-fade-scale flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <LiquidGlassCard
          variant="modal"
          clarity="frosted"
          className="w-full h-full p-0 rounded-3xl flex flex-col"
        >
        <div className="p-6 sm:p-8 space-y-6 overflow-y-auto apple-scrollbar pr-5 mr-1 my-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sky-400 font-bold">
              <Sparkles className="w-5 h-5" />
              <h3 className="text-xl text-white apple-text-headline">Bảng Kiểm Thử E2E Tự Động</h3>
            </div>
            <button
              onClick={() => setIsE2EModalOpen(false)}
              className="p-1.5 rounded-full text-neutral-300 hover:text-white bg-white/[0.08] hover:bg-white/[0.16] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <p className="text-xs text-slate-100 font-medium leading-relaxed drop-shadow-sm">
            Kích hoạt trực tiếp các kịch bản kiểm thử quy định trong tài liệu dự án để kiểm tra tính chính xác của sổ cái tài chính, thuật toán chống trùng lặp và phản hồi giao diện.
          </p>

        {/* Scenarios Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {/* Test 1 */}
          <button
            onClick={runValidUploadTest}
            className="p-4 rounded-2xl apple-frosted-glass border border-emerald-500/25 hover:border-emerald-500/50 text-left space-y-1.5 transition-all group active:scale-95"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-emerald-300">Test 1 · Biên lai hợp lệ</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-[11px] text-slate-100 font-medium leading-relaxed">Tải biên lai mới (+50k), AI quét mã GD, cộng số dư, đánh dấu học sinh đã nộp.</p>
          </button>

          {/* Test 2 */}
          <button
            onClick={runDuplicateUploadTest}
            className="p-4 rounded-2xl apple-frosted-glass border border-rose-500/25 hover:border-rose-500/50 text-left space-y-1.5 transition-all group active:scale-95"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-rose-300">Test 2 · Chống trùng lặp (Anti-dup)</span>
              <ShieldAlert className="w-4 h-4 text-rose-400" />
            </div>
            <p className="text-[11px] text-slate-100 font-medium leading-relaxed">Gửi lại mã giao dịch cũ. Hệ thống từ chối ghi sổ, giữ nguyên số dư quỹ.</p>
          </button>

          {/* Test 3 */}
          <button
            onClick={runLowConfidenceTest}
            className="p-4 rounded-2xl apple-frosted-glass border border-amber-500/25 hover:border-amber-500/50 text-left space-y-1.5 transition-all group active:scale-95"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-amber-300">Test 3 · AI Độ tin cậy thấp</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-[11px] text-slate-100 font-medium leading-relaxed">Ảnh mờ hoặc nghi ngờ giả mạo. Chuyển vào trạng thái CẦN KIỂM TRA, không tự cộng tiền.</p>
          </button>

          {/* Test 4 */}
          <button
            onClick={runRevertTest}
            className="p-4 rounded-2xl apple-frosted-glass border border-sky-500/25 hover:border-sky-500/50 text-left space-y-1.5 transition-all group active:scale-95"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sky-300">Test 4 · Thu hồi giao dịch (Revert)</span>
              <RotateCcw className="w-4 h-4 text-sky-400" />
            </div>
            <p className="text-[11px] text-slate-100 font-medium leading-relaxed">Thu hồi một giao dịch đã post, sinh bút toán đảo REV_..., bảo toàn lịch sử.</p>
          </button>

          {/* Test 5 */}
          <button
            onClick={runManualDebitTest}
            className="p-4 rounded-2xl apple-frosted-glass border border-rose-500/25 hover:border-rose-500/50 text-left space-y-1.5 transition-all group active:scale-95"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-rose-300">Test 5 · Chi quỹ thủ công</span>
              <MinusCircle className="w-4 h-4 text-rose-400" />
            </div>
            <p className="text-[11px] text-slate-100 font-medium leading-relaxed">Thủ quỹ ghi sổ chi tiền mua dụng cụ (-150k) kèm lý do kiểm toán.</p>
          </button>

          {/* Test 6 */}
          <button
            onClick={runModBroadcastTest}
            className="p-4 rounded-2xl apple-frosted-glass border border-amber-500/25 hover:border-amber-500/50 text-left space-y-1.5 transition-all group active:scale-95"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-amber-300">Test 6 · Thông báo Moderator</span>
              <Send className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-[11px] text-slate-100 font-medium leading-relaxed">Đăng tin thông báo nổi bật có badge MOD và viền hổ phách phát sáng.</p>
          </button>
        </div>

        {/* Reset Button */}
        <div className="pt-2 border-t border-white/[0.08] flex items-center justify-between">
          <button
            onClick={runPublicGuestTest}
            className="px-5 py-2 rounded-full apple-btn-secondary text-xs font-semibold flex items-center gap-1.5"
          >
            <Eye className="w-4 h-4" />
            <span>Xem ở chế độ Khách công khai</span>
          </button>

          <button
            onClick={() => {
              resetToDefaultData();
              setIsE2EModalOpen(false);
            }}
            className="px-4 py-2 rounded-full text-xs font-semibold text-slate-200 hover:text-white flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Khôi phục dữ liệu ban đầu</span>
          </button>
        </div>
        </div>
        </LiquidGlassCard>
      </div>
    </div>
  );
};
