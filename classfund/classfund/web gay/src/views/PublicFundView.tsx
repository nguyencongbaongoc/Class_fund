import React from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { formatVND, MOCK_BANK_ACCOUNT, ASSET_PATHS } from '../data/mockDatabase';
import { 
  ShieldCheck, 
  QrCode, 
  Copy, 
  Check, 
  Heart,
  ChevronRight
} from 'lucide-react';

export const PublicFundView: React.FC = () => {
  const { balances, campaign, ledgerEntries, setCurrentTab, addToast } = useApp();
  const [copied, setCopied] = React.useState(false);

  const verifiedEntries = ledgerEntries.filter(e => e.status === 'VERIFIED').slice(0, 6);

  const handleCopy = () => {
    navigator.clipboard.writeText(MOCK_BANK_ACCOUNT.account_number);
    setCopied(true);
    addToast({
      type: 'success',
      title: 'Đã copy số tài khoản',
      description: MOCK_BANK_ACCOUNT.account_number
    });
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-8 md:space-y-12 animate-in fade-in duration-300">
      {/* Public Trust Banner (Frosted Liquid Glass Hero) */}
      <LiquidCard variant="elevated" clarity="frosted" className="p-6 sm:p-10 md:p-12 border border-white/[0.12] shadow-2xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Cổng Thông Tin Công Khai Minh Bạch Lớp 12A1</span>
            </div>
            
            <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight apple-text-headline">
              Báo Cáo Tài Chính Lớp.
            </h1>
            
            <p className="text-xs sm:text-sm text-neutral-400 max-w-xl leading-relaxed">
              Mọi biến động thu chi được cập nhật tự động theo thời gian thực từ sổ cái kế toán bất biến. Phụ huynh và học sinh có thể theo dõi và đối soát bất cứ lúc nào.
            </p>
          </div>

          <div className="p-6 rounded-2xl apple-frosted-glass border border-white/10 text-right shrink-0">
            <span className="text-[11px] font-semibold text-neutral-400 uppercase tracking-widest block">Số dư quỹ hiện có</span>
            <span className="text-3xl sm:text-4xl font-extrabold text-white font-tabular block mt-1 apple-text-headline">
              {formatVND(balances.currentBalance)}
            </span>
            <span className="text-[10px] text-emerald-400 font-medium">✓ Đã kiểm toán qua AI</span>
          </div>
        </div>
      </LiquidCard>

      {/* 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Summary Metrics & Campaign Progress */}
        <div className="lg:col-span-2 space-y-6">
          {/* Income & Expense Duo */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <LiquidCard variant="clear" clarity="clear">
              <span className="text-xs font-medium text-neutral-400">Tổng các khoản nạp</span>
              <p className="text-2xl sm:text-3xl font-extrabold text-emerald-400 mt-1.5 font-tabular">
                +{formatVND(balances.totalCredit)}
              </p>
              <p className="text-xs text-neutral-400 mt-2">Bao gồm đóng quỹ học sinh & hỗ trợ từ hội phụ huynh</p>
            </LiquidCard>

            <LiquidCard variant="clear" clarity="clear">
              <span className="text-xs font-medium text-neutral-400">Tổng các khoản đã chi</span>
              <p className="text-2xl sm:text-3xl font-extrabold text-rose-400 mt-1.5 font-tabular">
                -{formatVND(balances.totalDebit)}
              </p>
              <p className="text-xs text-neutral-400 mt-2">In ấn đề cương thi & nước uống học sinh</p>
            </LiquidCard>
          </div>

          {/* Campaign Progress Card */}
          <LiquidCard className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-medium text-sky-400">Đợt thu hiện tại</span>
                <p className="text-lg font-bold text-white mt-0.5">{campaign.title}</p>
              </div>
              <span className="text-sm font-bold text-white font-tabular">
                {campaign.paid_students_count} / {campaign.target_students_count} đã nộp
              </span>
            </div>

            <div className="w-full h-2 rounded-full bg-white/[0.08] overflow-hidden">
              <div 
                className="h-full rounded-full bg-gradient-to-r from-sky-500 to-sky-400 shadow-sm transition-all"
                style={{ width: `${(campaign.paid_students_count / campaign.target_students_count) * 100}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-xs text-neutral-400 pt-1">
              <span>Định mức: {formatVND(campaign.expected_amount_per_student)} / học sinh</span>
              <span>Tổng đã thu: {formatVND(campaign.total_collected_amount)}</span>
            </div>
          </LiquidCard>

          {/* Public Transactions List */}
          <LiquidCard className="p-0 overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-white/[0.08] flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Lịch sử thu chi công khai gần nhất</h3>
              <span className="text-xs text-neutral-400 font-tabular">{verifiedEntries.length} giao dịch gần nhất</span>
            </div>

            <div className="divide-y divide-white/[0.04]">
              {verifiedEntries.map((tx) => (
                <div key={tx.id} className="p-4 flex items-center justify-between gap-4 hover:bg-white/[0.02] transition-colors">
                  <div>
                    <p className="text-sm font-semibold text-white">{tx.sender_name}</p>
                    <div className="flex items-center gap-2 text-xs text-neutral-400 mt-0.5">
                      <span>{tx.created_at}</span>
                      <span aria-hidden="true" className="text-neutral-600">·</span>
                      <span className="font-mono text-neutral-300">{tx.transaction_code}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-bold font-tabular ${tx.type === 'CREDIT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {tx.type === 'CREDIT' ? '+' : '-'}{formatVND(tx.amount)}
                    </p>
                    <p className="text-[11px] text-neutral-500">{tx.note || 'Không có ghi chú'}</p>
                  </div>
                </div>
              ))}
            </div>
          </LiquidCard>
        </div>

        {/* Right: VietQR Mini Card & Donate Me Link */}
        <div className="space-y-6">
          <div className="rounded-3xl apple-card-elevated p-6 border border-white/[0.1] shadow-2xl space-y-4 text-center">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.06] border border-white/10 text-neutral-300 text-xs">
              <QrCode className="w-3.5 h-3.5 text-sky-400" />
              <span>Quét mã VietQR nộp tiền</span>
            </div>

            <div className="w-48 h-48 mx-auto rounded-2xl overflow-hidden bg-white p-2.5 shadow-lg border border-white/20">
              <img
                src={MOCK_BANK_ACCOUNT.qr_image_url}
                alt="VietQR"
                referrerPolicy="no-referrer"
                className="w-full h-full object-contain"
              />
            </div>

            <div className="space-y-1">
              <p className="font-bold text-white text-base">{MOCK_BANK_ACCOUNT.account_name}</p>
              <p className="text-xs text-neutral-300 font-mono">{MOCK_BANK_ACCOUNT.account_number}</p>
              <p className="text-[11px] text-neutral-400">{MOCK_BANK_ACCOUNT.bank_name}</p>
            </div>

            <button
              onClick={handleCopy}
              className="w-full min-h-[44px] rounded-full apple-btn-primary text-xs font-semibold flex items-center justify-center gap-1.5 shadow-md active:scale-95 transition-all"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? 'Đã sao chép STK' : 'Sao chép số tài khoản'}</span>
            </button>

            <button
              onClick={() => setCurrentTab('upload')}
              className="w-full min-h-[44px] rounded-full apple-btn-secondary text-xs font-medium flex items-center justify-center gap-1.5 active:scale-95 transition-all"
            >
              <span>Tải ảnh biên lai lên</span>
              <ChevronRight className="w-4 h-4 text-neutral-400" />
            </button>
          </div>

          {/* Donate Me mini link */}
          <div 
            onClick={() => setCurrentTab('donate')}
            className="rounded-3xl apple-frosted-glass border border-white/[0.1] p-5 hover:border-white/25 cursor-pointer transition-all flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                <Heart className="w-4 h-4 fill-rose-500/40" />
              </div>
              <div>
                <p className="text-xs font-bold text-white">Ủng hộ nhóm phát triển?</p>
                <p className="text-[11px] text-neutral-400">Gặp gỡ Hải, Minh và Ngọc tại trang Donate Me</p>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-neutral-400" />
          </div>
        </div>
      </div>
    </div>
  );
};
