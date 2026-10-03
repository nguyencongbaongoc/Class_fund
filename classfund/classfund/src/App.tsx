import React, { useRef, useState, useEffect } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { ViewTab } from './types';
import { Navbar } from './components/common/Navbar';
import { MobileTabBar } from './components/common/MobileTabBar';
import { ToastContainer } from './components/common/ToastContainer';
import { FrostedContextMenu } from './components/common/FrostedContextMenu';
import { DashboardView } from './views/DashboardView';
import { LedgerView } from './views/LedgerView';
import { UploadReceiptView } from './views/UploadReceiptView';
import { CampaignView } from './views/CampaignView';
import { ChatView } from './views/ChatView';
import { BankQRView } from './views/BankQRView';
import { DonateView } from './views/DonateView';
import { PublicFundView } from './views/PublicFundView';
import { GuestChatPage } from './pages/GuestChatPage';
import { TransactionDetailModal } from './components/modals/TransactionDetailModal';
import { ManualExpenseModal } from './components/modals/ManualExpenseModal';
import { CreateCampaignModal } from './components/modals/CreateCampaignModal';
import { E2ETesterModal } from './components/modals/E2ETesterModal';
import { WallpaperModal } from './components/modals/WallpaperModal';
import { ASSET_PATHS } from './data/mockDatabase';
import { initGlobalSoundEffects } from './utils/soundEffects';

const AppBackground: React.FC = () => {
  const { currentWallpaper } = useApp();
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      <img
        key={currentWallpaper}
        src={currentWallpaper}
        alt="Desktop Wallpaper"
        referrerPolicy="no-referrer"
        className="w-full h-full object-cover object-center scale-105 transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]"
      />
      {/* Delicate Scrim for High Glass Transparency & High Legibility */}
      <div className="absolute inset-0 bg-slate-950/25 backdrop-blur-[0.5px]" />
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/50 via-transparent to-slate-950/20" />
    </div>
  );
};

const PerimeterGlowOverlay: React.FC = () => {
  const { isPerimeterGlowActive } = useApp();
  if (!isPerimeterGlowActive) return null;

  return (
    <div className="fixed inset-0 pointer-events-none z-[99999] transition-all duration-700 ease-out">
      {/* Outer luminous perimeter glow for 3 seconds */}
      <div className="absolute inset-0 border-[5px] border-amber-300 shadow-[inset_0_0_90px_rgba(251,191,36,0.7),0_0_80px_rgba(251,191,36,0.9),inset_0_0_35px_rgba(245,158,11,0.95)] animate-pulse" />
      <div className="absolute top-0 left-0 w-28 h-28 border-t-8 border-l-8 border-amber-200 shadow-[0_0_35px_rgba(251,191,36,1)]" />
      <div className="absolute top-0 right-0 w-28 h-28 border-t-8 border-r-8 border-amber-200 shadow-[0_0_35px_rgba(251,191,36,1)]" />
      <div className="absolute bottom-0 left-0 w-28 h-28 border-b-8 border-l-8 border-amber-200 shadow-[0_0_35px_rgba(251,191,36,1)]" />
      <div className="absolute bottom-0 right-0 w-28 h-28 border-b-8 border-r-8 border-amber-200 shadow-[0_0_35px_rgba(251,191,36,1)]" />
    </div>
  );
};

const MainContent: React.FC = () => {
  const { currentTab } = useApp();
  const prevTabRef = useRef<ViewTab>(currentTab);
  const [slideDirection, setSlideDirection] = useState<'right' | 'left'>('right');

  const tabOrder: ViewTab[] = [
    'dashboard',
    'ledger',
    'upload',
    'campaign',
    'chat',
    'guest-chat',
    'bank',
    'donate',
    'public',
  ];

  useEffect(() => {
    const prevIdx = tabOrder.indexOf(prevTabRef.current);
    const currIdx = tabOrder.indexOf(currentTab);
    if (currIdx >= prevIdx) {
      setSlideDirection('right');
    } else {
      setSlideDirection('left');
    }
    prevTabRef.current = currentTab;
  }, [currentTab]);

return (
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 pb-28 lg:pb-16 overflow-hidden">
        {/* Apple-style Synchronized Sliding View on every tab switch */}
        <div 
          key={currentTab} 
          className={slideDirection === 'right' ? 'animate-slide-from-right' : 'animate-slide-from-left'}
        >
          {currentTab === 'dashboard' && <DashboardView />}
          {currentTab === 'ledger' && <LedgerView />}
          {currentTab === 'upload' && <UploadReceiptView />}
          {currentTab === 'campaign' && <CampaignView />}
          {currentTab === 'chat' && <ChatView />}
          {currentTab === 'guest-chat' && <GuestChatPage />}
          {currentTab === 'bank' && <BankQRView />}
          {currentTab === 'donate' && <DonateView />}
          {currentTab === 'public' && <PublicFundView />}
        </div>
      </main>
    );
};

export default function App() {
  useEffect(() => {
    initGlobalSoundEffects();
  }, []);

  return (
    <AppProvider>
      <div className="min-h-screen bg-slate-950 text-[#f5f5f7] relative selection:bg-sky-500/30 selection:text-white">
        {/* Dynamic Apple Wallpaper with Smooth Fade */}
        <AppBackground />

        {/* Foreground Content Stack */}
        <div id="app-main-content" className="relative z-10 flex flex-col min-h-screen">
          <Navbar />
          <div className="flex-1">
            <MainContent />
          </div>
          
          {/* Apple-style Mobile Bottom Tab Bar */}
          <MobileTabBar />
        </div>

        {/* Morphing Frosted Glass Context Menu (Right Click anywhere) */}
        <FrostedContextMenu />

        {/* Modals & Toasts */}
        <TransactionDetailModal />
        <ManualExpenseModal />
        <CreateCampaignModal />
        <E2ETesterModal />
        <WallpaperModal />
        <ToastContainer />

        {/* 3-Second Perimeter Luminous Glow Easter Egg */}
        <PerimeterGlowOverlay />
      </div>
    </AppProvider>
  );
}
