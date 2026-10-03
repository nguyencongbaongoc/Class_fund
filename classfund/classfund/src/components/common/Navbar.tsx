import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { ViewTab, UserRole } from '../../types';
import { LiquidGlassCard } from './LiquidGlassCard';
import { 
  Sparkles, 
  Check, 
  ChevronDown,
  Image as ImageIcon
} from 'lucide-react';
import { playLiquidPop, playSuccessChime } from '../../utils/soundEffects';

export const Navbar: React.FC = () => {
  const { 
    currentTab, 
    setCurrentTab, 
    currentUser, 
    switchRole, 
    setIsE2EModalOpen,
    setIsWallpaperModalOpen,
    isSecretWallpaperUnlocked,
    unlockSecretWallpaper,
    triggerPerimeterGlow,
    addToast
  } = useApp();

  const [roleDropdownOpen, setRoleDropdownOpen] = useState(false);
  const consecutiveClicksRef = useRef(0);
  const lastClickTimestampRef = useRef(0);

  const handleLogoClick = () => {
    setCurrentTab('dashboard');

    if (isSecretWallpaperUnlocked) {
      return;
    }

    const now = Date.now();
    // Must be continuous rapid clicks (interval <= 700ms between each click)
    if (now - lastClickTimestampRef.current <= 700) {
      consecutiveClicksRef.current += 1;
    } else {
      consecutiveClicksRef.current = 1;
    }
    lastClickTimestampRef.current = now;

    // Secret trigger at 30 consecutive clicks
    if (consecutiveClicksRef.current >= 30) {
      consecutiveClicksRef.current = 0;
      lastClickTimestampRef.current = 0;
      unlockSecretWallpaper();
      triggerPerimeterGlow();
      playSuccessChime();
    }
  };

  const navContainerRef = useRef<HTMLDivElement>(null);
  const [indicatorStyle, setIndicatorStyle] = useState<{ left: number; width: number; opacity: number }>({
    left: 0,
    width: 0,
    opacity: 0,
  });

  const navItems: { tab: ViewTab; label: string }[] = [
    { tab: 'dashboard', label: 'Dashboard' },
    { tab: 'ledger', label: 'Sổ quỹ' },
    { tab: 'upload', label: 'Nộp biên lai' },
    { tab: 'campaign', label: 'Đợt thu' },
    { tab: 'chat', label: 'Chat lớp' },
    { tab: 'bank', label: 'VietQR' },
    { tab: 'donate', label: 'Donate me' },
  ];

  const roles: { role: UserRole; title: string; desc: string }[] = [
    { role: 'TREASURER', title: 'Thủ quỹ (Owner)', desc: 'Quyền cao nhất: Revert, Chi quỹ, Quản lý đợt thu' },
    { role: 'MODERATOR', title: 'Moderator (Lớp phó)', desc: 'Ghim thông báo [MOD], duyệt biên lai' },
    { role: 'MEMBER', title: 'Thành viên (Học sinh)', desc: 'Nộp biên lai, xem trạng thái, chat lớp' },
    { role: 'PUBLIC', title: 'Khách công khai', desc: 'Xem số dư & mã VietQR, không sửa dữ liệu' },
  ];

  // Update sliding pill indicator position whenever currentTab changes
  useEffect(() => {
    const updatePill = () => {
      if (navContainerRef.current) {
        const activeBtn = navContainerRef.current.querySelector<HTMLElement>(`[data-tab="${currentTab}"]`);
        if (activeBtn) {
          setIndicatorStyle({
            left: activeBtn.offsetLeft,
            width: activeBtn.offsetWidth,
            opacity: 1,
          });
        }
      }
    };

    updatePill();
    window.addEventListener('resize', updatePill);
    return () => window.removeEventListener('resize', updatePill);
  }, [currentTab]);

  return (
    <header className="sticky top-0 z-40 w-full bg-slate-950/20 backdrop-blur-2xl border-b border-white/[0.12] transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        {/* Zone 1: Apple-style Brand Wordmark */}
        <button
          onClick={handleLogoClick}
          className="flex items-center gap-2.5 text-left group transition-transform active:scale-95 shrink-0 select-none cursor-pointer"
          title="ClassFund"
        >
          <div className="w-8 h-8 rounded-xl bg-white/10 backdrop-blur-md border border-white/25 flex items-center justify-center shadow-lg group-hover:border-white/50 transition-colors">
            <span className="text-white text-xs font-bold font-mono">CF</span>
          </div>
          <span className="text-base font-bold tracking-tight text-white group-hover:text-neutral-200 transition-colors drop-shadow-sm hidden sm:inline">
            ClassFund
          </span>
        </button>

        {/* Zone 2: Translucent Liquid Glass Nav Pill */}
        <nav 
          ref={navContainerRef}
          className="hidden lg:flex items-center bg-neutral-900/30 hover:bg-neutral-900/40 backdrop-blur-3xl border border-white/20 rounded-full p-1 shadow-2xl relative transition-colors"
        >
          {/* Smooth Sliding Pill Indicator */}
          <div
            className="absolute top-1 bottom-1 rounded-full border border-white/40 bg-white/20 shadow-[0_2px_14px_rgba(255,255,255,0.2)] pointer-events-none transition-all duration-350 ease-[cubic-bezier(0.16,1,0.3,1)] z-0"
            style={{
              left: `${indicatorStyle.left}px`,
              width: `${indicatorStyle.width}px`,
              opacity: indicatorStyle.opacity,
            }}
          />

          {navItems.map((item) => {
            const isActive = currentTab === item.tab;
            return (
              <button
                key={item.tab}
                data-tab={item.tab}
                onClick={() => setCurrentTab(item.tab)}
                className={`relative z-10 px-3 py-1 text-xs font-medium rounded-full transition-colors duration-200 whitespace-nowrap ${
                  isActive
                    ? 'text-white font-bold drop-shadow-sm'
                    : 'text-neutral-300 hover:text-white'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Zone 3: Actions (Wallpaper, E2E Tester & Role Switcher) */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          {/* Wallpaper Switcher Trigger */}
          <button
            onClick={() => setIsWallpaperModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-neutral-100 text-xs font-medium transition-all active:scale-95 shadow-sm backdrop-blur-md"
            title="Đổi hình nền (Trừu tượng, Phong cảnh, Phái đẹp)"
          >
            <ImageIcon className="w-3.5 h-3.5 text-pink-400" />
            <span className="hidden sm:inline">Hình nền</span>
          </button>

          {/* E2E Test Scenarios trigger */}
          <button
            onClick={() => setIsE2EModalOpen(true)}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-neutral-100 text-xs font-medium transition-all active:scale-95 shadow-sm backdrop-blur-md"
            title="Mở bảng kiểm thử 16 kịch bản E2E"
          >
            <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            <span className="whitespace-nowrap">Test E2E</span>
          </button>

          {/* Role selector dropdown */}
          <div className="relative">
            <button
              onClick={() => {
                setRoleDropdownOpen(!roleDropdownOpen);
              }}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-neutral-900/35 hover:bg-neutral-900/50 backdrop-blur-xl text-xs font-medium text-white border border-white/20 transition-all active:scale-95 shadow-md"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="truncate max-w-[90px] sm:max-w-[130px] font-semibold">
                {currentUser.role === 'TREASURER' && 'Thủ quỹ'}
                {currentUser.role === 'MODERATOR' && 'Moderator'}
                {currentUser.role === 'MEMBER' && 'Học sinh'}
                {currentUser.role === 'PUBLIC' && 'Khách'}
              </span>
              <ChevronDown className={`w-3.5 h-3.5 text-neutral-300 transition-transform ${roleDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {roleDropdownOpen && (
              <div 
                className="absolute right-0 mt-2 w-72 rounded-3xl apple-card-modal p-2.5 shadow-2xl z-50 animate-apple-fade-scale"
                onMouseLeave={() => setRoleDropdownOpen(false)}
              >
                <div className="px-3 py-2 border-b border-white/[0.08] mb-1">
                  <p className="text-[11px] font-bold text-sky-200 uppercase tracking-wider">Phân quyền (RBAC)</p>
                  <p className="text-xs text-white font-bold truncate mt-0.5">{currentUser.name}</p>
                </div>
                <div className="space-y-1">
                  {roles.map((r) => {
                    const isSelected = currentUser.role === r.role;
                    return (
                      <button
                        key={r.role}
                        onClick={() => {
                          switchRole(r.role);
                          setRoleDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3.5 py-2.5 rounded-2xl text-xs flex items-start gap-2.5 transition-all ${
                          isSelected 
                            ? 'bg-sky-500/25 text-white font-bold border border-sky-400/40 shadow-sm' 
                            : 'text-neutral-200 hover:bg-white/[0.12] hover:text-white'
                        }`}
                      >
                        <div className="mt-0.5 shrink-0">
                          {isSelected ? (
                            <Check className="w-4 h-4 text-sky-400" />
                          ) : (
                            <div className="w-4 h-4 rounded-full border border-neutral-500" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-white">{r.title}</p>
                          <p className="text-[11px] text-slate-200 leading-snug">{r.desc}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
