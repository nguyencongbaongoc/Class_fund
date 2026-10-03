import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { MOCK_BANK_ACCOUNT, ASSET_PATHS } from '../data/mockDatabase';
import { 
  Copy, 
  Check, 
  ShieldCheck, 
  QrCode, 
  Info,
  ChevronRight
} from 'lucide-react';

export const BankQRView: React.FC = () => {
  const { addToast, setCurrentTab } = useApp();
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(label);
    addToast({
      type: 'success',
      title: `Đã sao chép ${label}`,
      description: text
    });
    setTimeout(() => setCopiedField(null), 2500);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="text-center space-y-2">
        <span className="text-xs font-semibold text-sky-400 uppercase tracking-widest block">
          VietQR NAPAS 247
        </span>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight apple-text-headline">
          Chuyển Tiền Vào Quỹ Lớp.
        </h1>
        <p className="text-xs sm:text-sm text-neutral-400 max-w-lg mx-auto">
          Quét mã VietQR bằng bất kỳ ứng dụng ngân hàng nào để nộp quỹ tức thì. Thông tin tài khoản được định sẵn.
        </p>
      </div>

      {/* Main Bank Frosted Liquid Glass Card */}
      <LiquidCard variant="elevated" clarity="frosted" className="p-6 sm:p-10 border border-white/[0.12] shadow-2xl space-y-8">
        {/* VietQR Display Frame */}
        <div className="flex flex-col sm:flex-row items-center gap-8 pb-8 border-b border-white/[0.08]">
          <div className="w-56 h-56 sm:w-64 sm:h-64 rounded-2xl overflow-hidden bg-white p-3 shrink-0 shadow-2xl border border-white/20 relative group">
            <img
              src={MOCK_BANK_ACCOUNT.qr_image_url}
              alt="Mã VietQR Quỹ Lớp"
              referrerPolicy="no-referrer"
              className="w-full h-full object-contain"
            />
            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center p-3 text-center">
              <span className="text-white text-xs font-medium">
                Mã VietQR chính thức lớp 12A1
              </span>
            </div>
          </div>

          <div className="space-y-4 text-center sm:text-left flex-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Tài khoản chính thức lớp 12A1</span>
            </div>

            <div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight apple-text-headline">
                {MOCK_BANK_ACCOUNT.account_name}
              </h2>
              <p className="text-xs text-neutral-300 mt-1">
                {MOCK_BANK_ACCOUNT.bank_name}
              </p>
            </div>
            
            <p className="text-xs text-neutral-400 leading-relaxed">
              Mọi khoản nộp qua mã QR sẽ được hệ thống AI đối soát mã giao dịch tự động và khớp với danh sách đóng quỹ.
            </p>
          </div>
        </div>

        {/* 1-Tap Copy Fields */}
        <div className="space-y-3">
          {/* Account Number */}
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 flex items-center justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">
                Số tài khoản (Chạm để sao chép)
              </p>
              <p className="text-xl sm:text-2xl font-extrabold text-white font-mono tracking-wider mt-0.5">
                {MOCK_BANK_ACCOUNT.account_number}
              </p>
            </div>
            
            <button
              onClick={() => copyToClipboard(MOCK_BANK_ACCOUNT.account_number, 'Số tài khoản')}
              className="min-h-[44px] px-5 py-2 rounded-full apple-btn-secondary text-xs font-semibold flex items-center gap-1.5 active:scale-95 transition-all shadow-sm"
            >
              {copiedField === 'Số tài khoản' ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400">Đã chép</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>Sao chép</span>
                </>
              )}
            </button>
          </div>

          {/* Syntax Example */}
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 flex items-center justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">
                Cú pháp nội dung chuyển
              </p>
              <p className="text-sm font-semibold text-sky-300 font-mono mt-0.5">
                {MOCK_BANK_ACCOUNT.transfer_syntax_example}
              </p>
            </div>
            
            <button
              onClick={() => copyToClipboard(MOCK_BANK_ACCOUNT.transfer_syntax_example, 'Nội dung chuyển khoản')}
              className="min-h-[44px] px-5 py-2 rounded-full apple-btn-secondary text-xs font-semibold flex items-center gap-1.5 active:scale-95 transition-all shadow-sm"
            >
              {copiedField === 'Nội dung chuyển khoản' ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400">Đã chép</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>Sao chép</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Step-by-step guidance */}
        <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2 text-xs text-neutral-300">
          <div className="flex items-center gap-1.5 font-semibold text-neutral-200">
            <Info className="w-4 h-4 text-sky-400" />
            <span>Quy trình 3 bước sau khi chuyển khoản:</span>
          </div>
          <ol className="list-decimal list-inside space-y-1 text-neutral-400 pl-1 leading-relaxed">
            <li>Lưu lại ảnh chụp màn hình xác nhận chuyển khoản thành công.</li>
            <li>Vào mục <button onClick={() => setCurrentTab('upload')} className="text-sky-400 underline font-medium">Nộp biên lai</button> và tải ảnh lên.</li>
            <li>Hệ thống AI đối soát trong 2 giây và cập nhật trạng thái "Đã nộp" trên danh sách lớp.</li>
          </ol>
        </div>
      </LiquidCard>
    </div>
  );
};
