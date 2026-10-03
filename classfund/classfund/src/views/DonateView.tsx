import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { LiquidCard } from '../components/common/LiquidCard';
import { ASSET_PATHS } from '../data/mockDatabase';
import { 
  Heart, 
  Sparkles, 
  Copy, 
  Code2, 
  Palette, 
  BrainCircuit,
  Check
} from 'lucide-react';
import { playLiquidPop, playSuccessChime } from '../utils/soundEffects';

export const DonateView: React.FC = () => {
  const { addToast } = useApp();
  const [copied, setCopied] = useState(false);
  const [selectedMember, setSelectedMember] = useState<'hai' | 'minh' | 'ngoc'>('hai');

  const teamMembers = {
    hai: {
      id: 'hai',
      name: 'Hà Đại Hải',
      roleBadge: 'Frontend Lead',
      subtitle: 'Hải · UI / UX & Frontend Architect',
      avatar: ASSET_PATHS.creatorAvatar,
      quote: '"Toàn bộ giao diện được mình thiết kế dựa trên ngôn ngữ thiết kế kính mờ Liquid Glass cao cấp: tối giản, sang trọng, tương tác chạm chuẩn xác và animation chuyển đổi fade+scale mượt mà không độ trễ."',
      highlightColor: 'text-sky-400',
      glowColor: 'bg-sky-500/10',
    },
    minh: {
      id: 'minh',
      name: 'Nguyễn Xuân Bảo Minh',
      roleBadge: 'Backend Lead',
      subtitle: 'Minh · Financial Core & Ledger Architect',
      avatar: 'https://i.pinimg.com/736x/f1/7f/b4/f17fb47fe4c3cb4476bce460eb5d91a6.jpg',
      quote: '"Hệ thống sổ cái bất biến (immutable double-entry ledger) với cơ chế băm SHA-256 chống giả mạo, engine đảo giao dịch (revert) tự động và phân quyền RBAC đa cấp độ đảm bảo an toàn tuyệt đối cho quỹ lớp."',
      highlightColor: 'text-emerald-400',
      glowColor: 'bg-emerald-500/10',
    },
    ngoc: {
      id: 'ngoc',
      name: 'Nguyễn Công Bảo Ngọc',
      roleBadge: 'AI & OCR Specialist',
      subtitle: 'Ngọc · Verification Pipeline & Computer Vision',
      avatar: 'https://i.pinimg.com/736x/e8/b9/76/e8b976238d4e0ed4f787bb0534a891f6.jpg',
      quote: '"Mô hình thị giác máy tính OCR bóc tách dữ liệu giao dịch ngân hàng theo thời gian thực: nhận diện số tiền, mã giao dịch, thời gian chuyển khoản và tính điểm tin cậy confidence score tự động đối soát."',
      highlightColor: 'text-purple-400',
      glowColor: 'bg-purple-500/10',
    },
  };

  const activeMember = teamMembers[selectedMember];

  const creatorBank = {
    account_name: 'HA DAI HAI',
    account_number: '0876680302',
    bank_name: 'MB Bank (Ngân hàng TMCP Quân Đội)',
    note: 'Ung ho Hai ClassFund',
  };

  const handleCopy = () => {
    playSuccessChime();
    navigator.clipboard.writeText(creatorBank.account_number);
    setCopied(true);
    addToast({
      type: 'success',
      title: 'Đã sao chép số tài khoản của Hải',
      description: `${creatorBank.account_number} · ${creatorBank.account_name} · MB Bank`,
    });
    setTimeout(() => setCopied(false), 2200);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-12 md:space-y-16 animate-in fade-in duration-300">
      {/* Editorial Header */}
      <div className="text-center space-y-3">
        <span className="text-xs font-semibold text-sky-400 uppercase tracking-widest block">
          Engineering &amp; Design Team
        </span>
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white apple-text-headline">
          Bộ Ba Phát Triển ClassFund.
        </h1>
        <p className="text-xs sm:text-base text-neutral-300 max-w-xl mx-auto leading-relaxed">
          Bấm vào từng thành viên bên dưới để xem hình ảnh chân dung và đóng góp chuyên môn của từng bạn.
        </p>
      </div>

      {/* Main Spotlight Card (Bấm vào ai hiện hình người đó) */}
      <LiquidCard variant="clear" className="p-6 sm:p-10 shadow-2xl relative overflow-hidden">
        {/* Subtle Ambient Studio Rim Lighting */}
        <div className={`absolute top-0 right-0 w-80 h-80 ${activeMember.glowColor} rounded-full blur-3xl pointer-events-none transition-colors duration-700`} />

        {/* Member Profile Showcase with Apple Spring Transition */}
        <div 
          key={activeMember.id}
          className="relative z-10 flex flex-col md:flex-row items-center gap-8 pb-4 animate-apple-fade-scale"
        >
          {/* Avatar Frame */}
          <div className="relative group shrink-0">
            <div className="w-40 h-40 sm:w-48 sm:h-48 rounded-3xl overflow-hidden border border-white/25 p-2 shadow-2xl relative bg-black/30 backdrop-blur-xl">
              <img
                src={activeMember.avatar}
                alt={activeMember.name}
                referrerPolicy="no-referrer"
                className="w-full h-full object-cover rounded-2xl transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:scale-105"
              />
            </div>
            <div className="absolute -bottom-2 -right-2 px-3.5 py-1.5 rounded-full bg-slate-900/80 backdrop-blur-xl border border-white/20 text-white text-[11px] font-semibold flex items-center gap-1.5 shadow-lg">
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              <span>{activeMember.roleBadge}</span>
            </div>
          </div>

          {/* Member Bio & Quote */}
          <div className="space-y-4 text-center md:text-left flex-1">
            <div className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-white/[0.08] border border-white/15 text-neutral-200 text-xs font-medium">
              <Heart className="w-3.5 h-3.5 text-rose-400 fill-rose-400" />
              <span>{activeMember.subtitle}</span>
            </div>

            <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight apple-text-headline">
              {activeMember.name}
            </h2>
            
            <p className="text-xs sm:text-sm text-neutral-300 leading-relaxed max-w-xl italic">
              {activeMember.quote}
            </p>
          </div>
        </div>
      </LiquidCard>

      {/* 3 Interactive Contributor Cards (Tách ra xa một chút) */}
      <div className="space-y-4">
        <div className="text-center md:text-left">
          <span className="text-xs font-bold text-neutral-400 uppercase tracking-wider">
            ✦ Chọn thành viên để xem thông tin:
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {/* Card 1: Hải */}
          <div
            onClick={() => {
              playLiquidPop();
              setSelectedMember('hai');
            }}
            className={`p-6 rounded-3xl cursor-pointer transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-1.5 active:scale-95 border ${
              selectedMember === 'hai'
                ? 'bg-sky-500/20 border-sky-400 ring-2 ring-sky-400/40 shadow-xl shadow-sky-500/20'
                : 'bg-slate-900/20 border-white/15 hover:border-white/35 hover:bg-slate-900/30'
            } backdrop-blur-xl space-y-3`}
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-2xl bg-sky-500/15 border border-sky-400/30 flex items-center justify-center text-sky-400">
                <Palette className="w-5 h-5" />
              </div>
              {selectedMember === 'hai' && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-sky-400 text-slate-950">
                  Đang xem
                </span>
              )}
            </div>
            <div>
              <p className="text-base font-bold text-white">Hải (Frontend)</p>
              <p className="text-xs text-sky-300 font-medium mt-0.5">Liquid Glass &amp; Optics</p>
            </div>
            <p className="text-xs text-neutral-300 leading-relaxed">
              Design system, hiệu ứng kính mờ trong suốt, kiến trúc giao diện tương tác Liquid Glass mượt mà.
            </p>
          </div>

          {/* Card 2: Minh */}
          <div
            onClick={() => {
              playLiquidPop();
              setSelectedMember('minh');
            }}
            className={`p-6 rounded-3xl cursor-pointer transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-1.5 active:scale-95 border ${
              selectedMember === 'minh'
                ? 'bg-emerald-500/20 border-emerald-400 ring-2 ring-emerald-400/40 shadow-xl shadow-emerald-500/20'
                : 'bg-slate-900/20 border-white/15 hover:border-white/35 hover:bg-slate-900/30'
            } backdrop-blur-xl space-y-3`}
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/15 border border-emerald-400/30 flex items-center justify-center text-emerald-400">
                <Code2 className="w-5 h-5" />
              </div>
              {selectedMember === 'minh' && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-400 text-slate-950">
                  Đang xem
                </span>
              )}
            </div>
            <div>
              <p className="text-base font-bold text-white">Minh (Backend)</p>
              <p className="text-xs text-emerald-300 font-medium mt-0.5">Financial Core &amp; Ledger</p>
            </div>
            <p className="text-xs text-neutral-300 leading-relaxed">
              Sổ cái bất biến, chống ghi trùng lặp, phân quyền RBAC đa cấp độ và engine Revert giao dịch.
            </p>
          </div>

          {/* Card 3: Ngọc */}
          <div
            onClick={() => {
              playLiquidPop();
              setSelectedMember('ngoc');
            }}
            className={`p-6 rounded-3xl cursor-pointer transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-1.5 active:scale-95 border ${
              selectedMember === 'ngoc'
                ? 'bg-purple-500/20 border-purple-400 ring-2 ring-purple-400/40 shadow-xl shadow-purple-500/20'
                : 'bg-slate-900/20 border-white/15 hover:border-white/35 hover:bg-slate-900/30'
            } backdrop-blur-xl space-y-3`}
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-2xl bg-purple-500/15 border border-purple-400/30 flex items-center justify-center text-purple-400">
                <BrainCircuit className="w-5 h-5" />
              </div>
              {selectedMember === 'ngoc' && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-400 text-slate-950">
                  Đang xem
                </span>
              )}
            </div>
            <div>
              <p className="text-base font-bold text-white">Ngọc (AI / OCR)</p>
              <p className="text-xs text-purple-300 font-medium mt-0.5">Verification Pipeline</p>
            </div>
            <p className="text-xs text-neutral-300 leading-relaxed">
              Nhận diện thông minh biên lai chuyển khoản, mã GD, số tiền và độ tin cậy confidence score.
            </p>
          </div>
        </div>
      </div>

      {/* Official VietQR Showcase Card (Tách ra xa một chút) */}
      <LiquidCard variant="clear" className="p-6 sm:p-10 shadow-2xl space-y-6">
        <div className="flex flex-col lg:flex-row items-center gap-8">
          {/* VietQR Frame */}
          <div className="w-56 h-56 sm:w-64 sm:h-64 rounded-3xl overflow-hidden bg-white p-3 shrink-0 shadow-2xl border border-white/20 relative group">
            <img
              src={ASSET_PATHS.vietQrMock}
              alt="VietQR HA DAI HAI"
              referrerPolicy="no-referrer"
              className="w-full h-full object-contain"
            />
            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center p-3 text-center rounded-2xl">
              <span className="text-white text-xs font-medium">
                Quét bằng ứng dụng ngân hàng bất kỳ (NAPAS 247)
              </span>
            </div>
          </div>

          {/* Bank Information Details */}
          <div className="space-y-5 flex-1 text-center lg:text-left">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.08] border border-white/15 text-neutral-300 text-xs font-medium">
              <span>☕ Ủng hộ trà sữa / cafe cho nhóm phát triển</span>
            </div>

            <div>
              <h3 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-mono">
                {creatorBank.account_name}
              </h3>
              <p className="text-xs sm:text-sm text-neutral-300 mt-1">
                {creatorBank.bank_name}
              </p>
            </div>

            {/* Account Number Box */}
            <div className="p-4 rounded-2xl bg-black/40 border border-white/15 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div>
                <span className="text-[10px] text-neutral-400 uppercase tracking-widest block font-medium">
                  Số tài khoản MB Bank
                </span>
                <span className="text-xl sm:text-2xl font-black text-white font-mono tracking-wider">
                  {creatorBank.account_number}
                </span>
              </div>

              <button
                onClick={handleCopy}
                className="w-full sm:w-auto px-5 py-2.5 rounded-full apple-btn-secondary text-xs font-bold flex items-center justify-center gap-2 shadow-md active:scale-95 transition-all"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-300">Đã chép!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    <span>Sao chép STK</span>
                  </>
                )}
              </button>
            </div>

            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4 text-xs text-neutral-400 pt-1">
              <span>Cú pháp gợi ý:</span>
              <span className="font-mono text-sky-400 font-semibold bg-sky-500/10 px-2 py-0.5 rounded border border-sky-400/20">
                {creatorBank.note}
              </span>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-white/10 text-center">
          <p className="text-[11px] text-neutral-400 italic">
            * Lưu ý minh bạch: Đây là tài khoản nhận ủng hộ của nhóm bạn Hải, Minh, Ngọc; hoàn toàn tách biệt khỏi tài khoản quỹ lớp 12A1.
          </p>
        </div>
      </LiquidCard>
    </div>
  );
};
