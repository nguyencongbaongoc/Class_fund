import React, { useState, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND } from '../data/mockDatabase';
import { TransactionStatus } from '../types';
import { 
  UploadCloud, 
  CheckCircle2, 
  AlertTriangle, 
  Loader2, 
  Sparkles, 
  ShieldAlert, 
  FileText
} from 'lucide-react';

export const UploadReceiptView: React.FC = () => {
  const { addLedgerEntry, ledgerEntries, addToast, setCurrentTab, currentUser } = useApp();
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [uploaderName, setUploaderName] = useState<string>(currentUser.name || '');
  const [extractedAmount, setExtractedAmount] = useState<number>(50000);
  const [extractedTxCode, setExtractedTxCode] = useState<string>('VCB' + Math.floor(1000000 + Math.random() * 9000000));
  const [extractedBank, setExtractedBank] = useState<string>('MB Bank');
  
  // Pipeline processing state
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [verificationResult, setVerificationResult] = useState<{
    status: TransactionStatus;
    confidence: number;
    reason?: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sample Presets for Fast Testing
  const handleSelectPreset = (type: 'VALID' | 'DUPLICATE' | 'LOW_CONFIDENCE') => {
    if (type === 'VALID') {
      const randomCode = 'MB' + Math.floor(1000000 + Math.random() * 9000000);
      setExtractedTxCode(randomCode);
      setExtractedAmount(50000);
      setExtractedBank('MB Bank');
      setUploaderName('Đỗ Quang Huy');
      setPreviewUrl('https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=600&auto=format&fit=crop&q=80');
      setVerificationResult(null);
    } else if (type === 'DUPLICATE') {
      const existingTx = ledgerEntries.find(e => e.status === 'VERIFIED');
      const dupCode = existingTx ? existingTx.transaction_code : 'VCB8921734';
      setExtractedTxCode(dupCode);
      setExtractedAmount(50000);
      setExtractedBank('MB Bank');
      setUploaderName('Học sinh gửi lại ảnh cũ');
      setPreviewUrl('https://images.unsplash.com/photo-1554224154-26032ffc0d07?w=600&auto=format&fit=crop&q=80');
      setVerificationResult(null);
    } else {
      setExtractedTxCode('MB_BLURRY_???');
      setExtractedAmount(50000);
      setExtractedBank('Ngân hàng không rõ');
      setUploaderName('Ảnh chụp rung lắc mờ số');
      setPreviewUrl('https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=600&auto=format&fit=crop&q=80');
      setVerificationResult(null);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setVerificationResult(null);
      setExtractedTxCode('MB' + Math.floor(1000000 + Math.random() * 9000000));
    }
  };

  const startProcessing = () => {
    if (!previewUrl) {
      addToast({ type: 'warning', title: 'Chưa có ảnh biên lai', description: 'Vui lòng chọn ảnh hoặc chọn mẫu thử nghiệm.' });
      return;
    }
    if (!uploaderName.trim()) {
      addToast({ type: 'warning', title: 'Thiếu tên người gửi', description: 'Vui lòng nhập họ và tên của người nộp ảnh.' });
      return;
    }

    setIsProcessing(true);
    setCurrentStep(1);
    setVerificationResult(null);

    // Step 1: Upload
    setTimeout(() => {
      setCurrentStep(2); // AI OCR
      
      // Step 2: OCR Analysis
      setTimeout(() => {
        setCurrentStep(3); // Anti-Duplicate Check
        
        // Step 3: Anti Duplicate & Business Rule Verification
        setTimeout(() => {
          setIsProcessing(false);
          setCurrentStep(4);

          // Check duplicate
          const isDuplicate = ledgerEntries.some(
            (tx) => tx.transaction_code.toUpperCase() === extractedTxCode.toUpperCase() && tx.status === 'VERIFIED'
          );

          if (isDuplicate) {
            setVerificationResult({
              status: 'DUPLICATE',
              confidence: 99.8,
              reason: `Mã giao dịch ${extractedTxCode} đã tồn tại trong sổ cái quỹ! Hệ thống chống trùng lặp đã tự động từ chối ghi sổ.`
            });
            addToast({
              type: 'error',
              title: 'Phát hiện biên lai trùng lặp!',
              description: `Mã ${extractedTxCode} đã được cộng quỹ trước đó. Giao dịch bị từ chối.`
            });
            return;
          }

          if (extractedTxCode.includes('???') || extractedTxCode.includes('BLURRY')) {
            setVerificationResult({
              status: 'NEEDS_REVIEW',
              confidence: 68.2,
              reason: 'Ảnh chụp chất lượng thấp, AI không đọc rõ mã giao dịch. Cần Thủ quỹ kiểm tra đối soát thủ công.'
            });
            addLedgerEntry({
              type: 'CREDIT',
              amount: extractedAmount,
              currency: 'VND',
              source: 'IMAGE',
              transaction_code: extractedTxCode,
              sender_name: uploaderName,
              uploaded_by: uploaderName,
              status: 'NEEDS_REVIEW',
              ai_confidence: 68.2,
              image_url: previewUrl,
              extracted_bank: extractedBank,
              note: 'Biên lai mờ số, chờ thủ quỹ xác minh ngân hàng',
            });
            addToast({
              type: 'warning',
              title: 'Chờ duyệt kiểm tra',
              description: 'AI đã chuyển giao dịch sang mục "Cần kiểm tra" cho thủ quỹ.'
            });
            return;
          }

          // Case Verified!
          setVerificationResult({
            status: 'VERIFIED',
            confidence: 99.4,
            reason: `Đã xác thực thành công. Mã GD: ${extractedTxCode}, Số tiền: ${formatVND(extractedAmount)}.`
          });

          addLedgerEntry({
            type: 'CREDIT',
            amount: extractedAmount,
            currency: 'VND',
            source: 'IMAGE',
            transaction_code: extractedTxCode,
            sender_name: uploaderName,
            uploaded_by: uploaderName,
            status: 'VERIFIED',
            ai_confidence: 99.4,
            image_url: previewUrl,
            extracted_bank: extractedBank,
            note: 'Nộp quỹ lớp qua chuyển khoản',
            campaign_id: 'camp_oct2026',
          });

          addToast({
            type: 'success',
            title: 'Xác minh thành công!',
            description: `Đã cộng ${formatVND(extractedAmount)} vào quỹ và cập nhật trạng thái đợt thu.`
          });
        }, 1000);
      }, 1000);
    }, 800);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="text-center space-y-2">
        <span className="text-xs font-semibold text-sky-400 uppercase tracking-widest block">
          AI Optical Verification
        </span>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight apple-text-headline">
          Nộp Biên Lai Chuyển Khoản.
        </h1>
        <p className="text-xs sm:text-sm text-slate-100 font-medium max-w-lg mx-auto leading-relaxed drop-shadow-sm">
          AI do bạn Ngọc phụ trách tự động đọc mã giao dịch, số tiền và thời gian. Quy trình 4 lớp bảo vệ ngăn ngừa trùng lặp tuyệt đối.
        </p>
      </div>

      {/* Preset Fast Testing Bar - Clear Liquid Glass */}
      <LiquidCard variant="clear" clarity="clear" className="p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-medium text-neutral-300">
            <Sparkles className="w-4 h-4 text-sky-400" />
            <span>Mẫu thử nghiệm nhanh:</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => handleSelectPreset('VALID')}
              className="px-3 py-1 rounded-full bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/25 text-emerald-300 text-xs font-medium transition-all"
            >
              1. Biên lai hợp lệ (+50k)
            </button>
            <button
              onClick={() => handleSelectPreset('DUPLICATE')}
              className="px-3 py-1 rounded-full bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/25 text-rose-300 text-xs font-medium transition-all"
            >
              2. Trùng lặp (Block)
            </button>
            <button
              onClick={() => handleSelectPreset('LOW_CONFIDENCE')}
              className="px-3 py-1 rounded-full bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/25 text-amber-300 text-xs font-medium transition-all"
            >
              3. Ảnh mờ (Review)
            </button>
          </div>
        </div>
      </LiquidCard>

      {/* Main Upload Frosted Frame - Frosted Liquid Glass */}
      <LiquidCard variant="elevated" clarity="frosted" className="p-6 sm:p-10 border border-white/[0.12] shadow-2xl space-y-6">
        {/* Drop zone / Upload trigger */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border border-dashed border-white/20 hover:border-sky-400/50 rounded-2xl p-6 sm:p-10 text-center cursor-pointer transition-all bg-white/[0.02] hover:bg-white/[0.04] group"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*"
            className="hidden"
          />

          {previewUrl ? (
            <div className="space-y-4">
              <div className="relative inline-block max-w-xs mx-auto rounded-2xl overflow-hidden p-1 border border-white/20 shadow-xl bg-black">
                <img
                  src={previewUrl}
                  alt="Ảnh biên lai"
                  referrerPolicy="no-referrer"
                  className="w-full h-48 object-cover rounded-xl"
                />
                <div className="absolute inset-0 bg-black/60 opacity-0 hover:opacity-100 transition-opacity rounded-xl flex items-center justify-center p-3">
                  <span className="text-xs text-white font-medium">Bấm để thay ảnh khác</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/10 flex items-center justify-center mx-auto text-sky-400 group-hover:scale-105 transition-transform shadow-lg">
                <UploadCloud className="w-6 h-6" />
              </div>
              <p className="text-sm font-semibold text-white">
                Kéo thả ảnh biên lai vào đây hoặc <span className="text-sky-400 underline">chọn từ máy</span>
              </p>
              <p className="text-xs text-neutral-400">
                Hỗ trợ PNG, JPG, WebP hoặc ảnh chụp màn hình ngân hàng
              </p>
            </div>
          )}
        </div>

        {/* Input Details */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-300">Tên người nộp / chuyển khoản *</label>
            <input
              type="text"
              value={uploaderName}
              onChange={(e) => setUploaderName(e.target.value)}
              placeholder="VD: Nguyễn Văn An"
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white text-xs sm:text-sm focus:outline-none focus:border-sky-400 transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-300">Mã giao dịch (AI trích xuất)</label>
            <input
              type="text"
              value={extractedTxCode}
              onChange={(e) => setExtractedTxCode(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-white text-xs sm:text-sm font-mono focus:outline-none focus:border-sky-400 transition-colors"
            />
          </div>
        </div>

        {/* Action Button */}
        <div>
          <button
            onClick={startProcessing}
            disabled={isProcessing}
            className="w-full min-h-[48px] rounded-full apple-btn-primary font-semibold text-sm flex items-center justify-center gap-2 shadow-lg shadow-sky-600/30 transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>AI đang phân tích & đối soát 4 lớp...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Gửi và Xác thực bằng AI</span>
              </>
            )}
          </button>
        </div>

        {/* Stepper */}
        {isProcessing && (
          <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/10 space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold text-neutral-300">
              <span>Tiến trình xử lý:</span>
              <span className="text-sky-400 font-mono">Bước {currentStep}/3</span>
            </div>
            <div className="space-y-2 text-xs">
              <div className={`flex items-center gap-2 ${currentStep >= 1 ? 'text-sky-300' : 'text-neutral-500'}`}>
                {currentStep > 1 ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Loader2 className="w-4 h-4 animate-spin" />}
                <span>1. Tải ảnh & tạo mã băm vân tay (SHA-256 fingerprint)</span>
              </div>
              <div className={`flex items-center gap-2 ${currentStep >= 2 ? 'text-sky-300' : 'text-neutral-500'}`}>
                {currentStep > 2 ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : currentStep === 2 ? <Loader2 className="w-4 h-4 animate-spin" /> : <div className="w-4 h-4 rounded-full border border-neutral-600" />}
                <span>2. AI OCR nhận diện Mã GD, Số tiền, Ngân hàng</span>
              </div>
              <div className={`flex items-center gap-2 ${currentStep >= 3 ? 'text-sky-300' : 'text-neutral-500'}`}>
                {currentStep > 3 ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : currentStep === 3 ? <Loader2 className="w-4 h-4 animate-spin" /> : <div className="w-4 h-4 rounded-full border border-neutral-600" />}
                <span>3. Kiểm tra chống ghi trùng lặp vào sổ cái</span>
              </div>
            </div>
          </div>
        )}

        {/* Verification Result Card */}
        {verificationResult && (
          <div className={`p-5 rounded-2xl border ${
            verificationResult.status === 'VERIFIED'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
              : verificationResult.status === 'DUPLICATE'
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
          }`}>
            <div className="flex items-start gap-3">
              {verificationResult.status === 'VERIFIED' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : verificationResult.status === 'DUPLICATE' ? (
                <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              )}
              
              <div className="space-y-1 flex-1">
                <div className="flex items-center justify-between">
                  <p className="font-bold text-sm">
                    {verificationResult.status === 'VERIFIED' && 'ĐÃ XÁC THỰC THÀNH CÔNG'}
                    {verificationResult.status === 'DUPLICATE' && 'TỪ CHỐI: TRÙNG LẶP GIAO DỊCH'}
                    {verificationResult.status === 'NEEDS_REVIEW' && 'CẦN KIỂM TRA ĐỐI SOÁT'}
                  </p>
                  <span className="text-xs font-mono">Độ tin cậy: {verificationResult.confidence}%</span>
                </div>
                <p className="text-xs leading-relaxed opacity-90">{verificationResult.reason}</p>

                {verificationResult.status === 'VERIFIED' && (
                  <div className="pt-2 flex items-center gap-3">
                    <button
                      onClick={() => setCurrentTab('ledger')}
                      className="text-xs underline font-semibold hover:text-white"
                    >
                      Xem trong sổ cái →
                    </button>
                    <button
                      onClick={() => setCurrentTab('campaign')}
                      className="text-xs underline font-semibold hover:text-white"
                    >
                      Xem tiến độ đợt thu →
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </LiquidCard>
    </div>
  );
};
