import React, { useRef, useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { ViewTab } from '../../types';
import { LiquidGlassCard } from './LiquidGlassCard';
import { 
  LayoutDashboard, 
  ReceiptText, 
  PlusCircle, 
  Users, 
  MessageSquare 
} from 'lucide-react';

export const MobileTabBar: React.FC = () => {
  const { currentTab, setCurrentTab } = useApp();
  const tabContainerRef = useRef<HTMLDivElement>(null);
  const [indicatorStyle, setIndicatorStyle] = useState<{ left: number; width: number; opacity: number }>({
    left: 0,
    width: 0,
    opacity: 0,
  });

  const tabs: { tab: ViewTab; label: string; icon: React.ReactNode; isAction?: boolean }[] = [
    { tab: 'dashboard', label: 'Tổng quan', icon: <LayoutDashboard className="w-5 h-5" /> },
    { tab: 'ledger', label: 'Sổ quỹ', icon: <ReceiptText className="w-5 h-5" /> },
    { 
      tab: 'upload', 
      label: 'Nộp ảnh', 
      icon: <PlusCircle className="w-6 h-6 text-sky-400" />,
      isAction: true 
    },
    { tab: 'campaign', label: 'Đợt thu', icon: <Users className="w-5 h-5" /> },
    { tab: 'chat', label: 'Chat lớp', icon: <MessageSquare className="w-5 h-5" /> },
  ];

  // Sliding pill indicator animation on tab change
  useEffect(() => {
    const updatePill = () => {
      if (tabContainerRef.current) {
        const activeBtn = tabContainerRef.current.querySelector<HTMLElement>(`[data-tab="${currentTab}"]`);
        if (activeBtn) {
          setIndicatorStyle({
            left: activeBtn.offsetLeft,
            width: activeBtn.offsetWidth,
            opacity: 1,
          });
        } else {
          setIndicatorStyle((prev) => ({ ...prev, opacity: 0 }));
        }
      }
    };

    updatePill();
    window.addEventListener('resize', updatePill);
    return () => window.removeEventListener('resize', updatePill);
  }, [currentTab]);

  return (
    <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 px-4 pb-4 pt-1 pointer-events-none">
      <div className="pointer-events-auto max-w-sm mx-auto shadow-2xl rounded-full">
        <LiquidGlassCard
          variant="clear"
          clarity="clear"
          roundedClass="rounded-full"
          className="h-16 rounded-full px-3 flex items-center justify-around relative"
        >
          {/* Inner container with relative positioning for the sliding indicator */}
          <div ref={tabContainerRef} className="w-full flex items-center justify-around relative">
            {/* Smooth Sliding Pill Indicator */}
            <div
              className="absolute top-0 bottom-0 rounded-2xl border border-white/35 bg-white/15 shadow-[0_2px_12px_rgba(255,255,255,0.18)] pointer-events-none transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] z-0"
              style={{
                left: `${indicatorStyle.left}px`,
                width: `${indicatorStyle.width}px`,
                opacity: indicatorStyle.opacity,
              }}
            />

            {tabs.map((t) => {
              const isActive = currentTab === t.tab;
              
              if (t.isAction) {
                return (
                  <button
                    key={t.tab}
                    data-tab={t.tab}
                    onClick={() => setCurrentTab(t.tab)}
                    className="relative -top-3 w-12 h-12 rounded-full bg-sky-500 hover:bg-sky-400 flex items-center justify-center shadow-lg shadow-sky-500/30 text-white active:scale-95 transition-all z-10"
                    aria-label={t.label}
                  >
                    {t.icon}
                  </button>
                );
              }

              return (
                <button
                  key={t.tab}
                  data-tab={t.tab}
                  onClick={() => setCurrentTab(t.tab)}
                  className={`relative z-10 flex flex-col items-center justify-center px-2 py-1 min-w-[50px] min-h-[44px] rounded-2xl transition-all duration-200 ${
                    isActive 
                      ? 'text-sky-300 font-semibold' 
                      : 'text-neutral-300 hover:text-white'
                  }`}
                >
                  <div className={`p-0.5 transition-transform ${isActive ? 'scale-110 text-white' : ''}`}>
                    {t.icon}
                  </div>
                  <span className="text-[10px] tracking-tight">{t.label}</span>
                </button>
              );
            })}
          </div>
        </LiquidGlassCard>
      </div>
    </div>
  );
};
