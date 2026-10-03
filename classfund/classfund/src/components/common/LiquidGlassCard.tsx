import React from 'react';

export interface LiquidGlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'elevated' | 'droplet' | 'mod' | 'clear' | 'frosted' | 'modal';
  clarity?: 'clear' | 'balanced' | 'frosted';
  className?: string;
  enableShader?: boolean;
  opacity?: number;
  blurAmount?: number;
  roundedClass?: string;
  interactive?: boolean;
}

export const LiquidGlassCard: React.FC<LiquidGlassCardProps> = ({
  children,
  variant = 'default',
  clarity,
  className = '',
  opacity,
  blurAmount,
  roundedClass = 'rounded-3xl',
  interactive = true,
  ...props
}) => {
  // Ultra-high transparency Apple glass (kính có độ trong suốt cao, thuần khiết)
  // Perfectly balanced between glass clarity and readable text
  let bgStyles = 'bg-slate-950/20';
  let borderStyles = 'border border-white/20';
  let shadowStyles = 'shadow-xl shadow-black/15';

  if (variant === 'modal') {
    bgStyles = 'bg-slate-950/50';
    borderStyles = 'border border-white/25';
    shadowStyles = 'shadow-2xl shadow-black/40';
  } else if (variant === 'elevated') {
    bgStyles = 'bg-slate-950/25';
    borderStyles = 'border border-white/20';
    shadowStyles = 'shadow-2xl shadow-black/20';
  }

  // Smooth spring interactive hover without any divider or horizontal lines
  const hoverStyles = interactive 
    ? 'hover:border-white/35 hover:bg-slate-950/25 hover:shadow-2xl hover:shadow-sky-500/10 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]' 
    : 'transition-all duration-300 ease-out';

  return (
    <div
      className={`relative overflow-hidden ${roundedClass} ${bgStyles} ${borderStyles} ${shadowStyles} ${hoverStyles} ${className}`}
      style={{
        backdropFilter: 'blur(20px) saturate(170%) brightness(105%)',
        WebkitBackdropFilter: 'blur(20px) saturate(170%) brightness(105%)',
        willChange: 'transform, backdrop-filter',
      }}
      {...props}
    >
      {/* Content wrapper - clean, no horizontal divider line */}
      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </div>
  );
};
