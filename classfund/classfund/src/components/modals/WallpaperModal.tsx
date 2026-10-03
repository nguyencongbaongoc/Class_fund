import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { LiquidGlassCard } from '../common/LiquidGlassCard';
import { WALLPAPERS, WALLPAPER_CATEGORIES } from '../../data/wallpapers';
import { X, Check, Image as ImageIcon, Sparkles, Mountain, Heart } from 'lucide-react';
import { playLiquidPop, playSuccessChime, playSheetTransition } from '../../utils/soundEffects';

export const WallpaperModal: React.FC = () => {
  const { 
    isWallpaperModalOpen, 
    setIsWallpaperModalOpen, 
    currentWallpaper, 
    setCurrentWallpaper,
    isSecretWallpaperUnlocked
  } = useApp();

  const [activeCategory, setActiveCategory] = useState<'abstract' | 'landscape' | 'beauty'>('abstract');

  if (!isWallpaperModalOpen) return null;

  const filteredWallpapers = WALLPAPERS.filter(wp => {
    if (wp.category !== activeCategory) return false;
    if (wp.isSecret && !isSecretWallpaperUnlocked) return false;
    return true;
  });

  const getCategoryIcon = (cat: 'abstract' | 'landscape' | 'beauty') => {
    switch (cat) {
      case 'abstract':
        return <Sparkles className="w-3.5 h-3.5 text-amber-400" />;
      case 'landscape':
        return <Mountain className="w-3.5 h-3.5 text-emerald-400" />;
      case 'beauty':
        return <Heart className="w-3.5 h-3.5 text-rose-400 fill-rose-400/30" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto animate-apple-fade-scale">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-md transition-opacity"
        onClick={() => setIsWallpaperModalOpen(false)}
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-4xl z-10 my-auto">
        <LiquidGlassCard
          variant="modal"
          className="p-6 sm:p-8 rounded-3xl overflow-hidden shadow-2xl border border-white/20"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-5 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-white/10 border border-white/20 flex items-center justify-center text-sky-400 shadow-lg">
                <ImageIcon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white tracking-tight apple-text-headline">
                  Bộ Sưu Tập Hình Nền
                </h3>
                <p className="text-xs text-neutral-300 mt-0.5">
                  Chọn hình nền nghệ thuật cao cấp — Giao diện kính mờ sẽ phản chiếu theo ảnh nền bạn chọn.
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                playSheetTransition();
                setIsWallpaperModalOpen(false);
              }}
              className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-neutral-300 hover:text-white flex items-center justify-center border border-white/15 transition-all active:scale-95"
              aria-label="Đóng"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Category Tabs */}
          <div className="flex items-center gap-2 py-5 overflow-x-auto scrollbar-none">
            {WALLPAPER_CATEGORIES.map((cat) => {
              const isActive = activeCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => {
                    playLiquidPop();
                    setActiveCategory(cat.id as any);
                  }}
                  className={`flex items-center gap-2 px-5 py-2 rounded-full text-xs font-bold transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] whitespace-nowrap active:scale-95 ${
                    isActive
                      ? 'bg-sky-500/30 text-white border border-sky-400/50 shadow-lg shadow-sky-500/20'
                      : 'bg-white/[0.06] hover:bg-white/[0.12] text-neutral-300 border border-white/10'
                  }`}
                >
                  {getCategoryIcon(cat.id as any)}
                  <span>{cat.label}</span>
                </button>
              );
            })}
          </div>

          {/* Wallpapers Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 max-h-[60vh] overflow-y-auto p-1 scrollbar-none">
            {filteredWallpapers.map((wp) => {
              const isSelected = currentWallpaper === wp.url;
              return (
                <div
                  key={wp.id}
                  onClick={() => {
                    playSuccessChime();
                    setCurrentWallpaper(wp.url);
                  }}
                  className={`group relative rounded-2xl overflow-hidden cursor-pointer border transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:scale-[1.03] active:scale-[0.98] aspect-video ${
                    isSelected
                      ? 'ring-2 ring-sky-400 border-sky-300 shadow-xl shadow-sky-500/30'
                      : 'border-white/15 hover:border-white/40 shadow-lg'
                  }`}
                >
                  {/* Image */}
                  <img
                    src={wp.url}
                    alt={wp.name}
                    referrerPolicy="no-referrer"
                    className="w-full h-full object-cover transition-transform duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:scale-110"
                    loading="lazy"
                  />

                  {/* Glass Overlay on Hover / Active */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent flex flex-col justify-end p-3 transition-opacity">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white drop-shadow-md truncate max-w-[80%]">
                        {wp.name}
                      </span>
                      {isSelected && (
                        <div className="w-5 h-5 rounded-full bg-sky-500 text-white flex items-center justify-center shadow-md">
                          <Check className="w-3 h-3 stroke-[3]" />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="pt-5 mt-4 border-t border-white/10 flex items-center justify-between text-xs text-neutral-400">
            <span>Tự động lưu và duy trì hình nền khi tải lại trang</span>
            <button
              onClick={() => setIsWallpaperModalOpen(false)}
              className="px-5 py-2 rounded-full apple-btn-primary font-bold text-xs"
            >
              Hoàn tất
            </button>
          </div>
        </LiquidGlassCard>
      </div>
    </div>
  );
};
