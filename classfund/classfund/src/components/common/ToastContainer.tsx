import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { LiquidGlassCard } from './LiquidGlassCard';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

interface ToastItemProps {
  toast: {
    id: string;
    type: 'success' | 'error' | 'info' | 'warning';
    title: string;
    description?: string;
  };
  onRemove: (id: string) => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onRemove }) => {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    // Automatically jump to the sky after 3.8s
    const timer = setTimeout(() => {
      triggerExit();
    }, 3800);

    return () => clearTimeout(timer);
  }, []);

  const triggerExit = () => {
    if (isExiting) return;
    setIsExiting(true);
    // After sky-jump rocket launch completes (440ms), remove from context
    setTimeout(() => {
      onRemove(toast.id);
    }, 440);
  };

  let icon = <Info className="w-5 h-5 text-sky-400 shrink-0" />;
  let glowAccent = 'shadow-[0_24px_60px_rgba(0,0,0,0.55),0_0_30px_rgba(56,189,248,0.22)]';

  if (toast.type === 'success') {
    icon = <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />;
    glowAccent = 'shadow-[0_24px_60px_rgba(0,0,0,0.55),0_0_30px_rgba(16,185,129,0.22)]';
  } else if (toast.type === 'error') {
    icon = <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />;
    glowAccent = 'shadow-[0_24px_60px_rgba(0,0,0,0.55),0_0_30px_rgba(244,63,94,0.22)]';
  } else if (toast.type === 'warning') {
    icon = <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />;
    glowAccent = 'shadow-[0_24px_60px_rgba(0,0,0,0.55),0_0_30px_rgba(245,158,11,0.22)]';
  }

  return (
    <div
      className={`pointer-events-auto ${glowAccent} ${
        isExiting ? 'animate-toast-sky-jump-exit' : 'animate-toast-sky-drop'
      } transition-all select-none rounded-3xl overflow-hidden`}
    >
      <LiquidGlassCard
        variant="clear"
        clarity="clear"
        className="p-4 rounded-3xl !border-0 flex items-start gap-3.5 bg-slate-900/20 backdrop-blur-2xl"
      >
        {/* Icon Core */}
        <div className="mt-0.5 shrink-0">
          {icon}
        </div>

        {/* Content with high contrast readability */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-white tracking-tight leading-snug drop-shadow-sm">{toast.title}</p>
          {toast.description && (
            <p className="text-xs text-neutral-200 mt-1 leading-relaxed">{toast.description}</p>
          )}
        </div>

        {/* Close Button: triggers sky jump immediately */}
        <button
          onClick={triggerExit}
          className="text-neutral-400 hover:text-white p-1 -mr-1 -mt-1 rounded-xl transition-colors active:scale-95"
          aria-label="Đóng thông báo"
        >
          <X className="w-4 h-4" />
        </button>
      </LiquidGlassCard>
    </div>
  );
};

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-5 right-5 z-50 flex flex-col gap-3 max-w-sm w-full pointer-events-none px-4 md:px-0">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
      ))}
    </div>
  );
};
