import React from 'react';
import { 
  Clock, Loader2, AlertTriangle, CheckCircle2, XCircle, AlertCircle, RotateCcw 
} from 'lucide-react';
import { MessageStatus, MESSAGE_STATUS_CONFIG } from '../../types/chat';

interface StatusBadgeProps {
  status: MessageStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  showIcon?: boolean;
  className?: string;
}

const StatusIcons: Record<MessageStatus, React.ComponentType<{ className?: string }>> = {
  pending: Clock,
  processing: Loader2,
  awaiting_review: AlertTriangle,
  posted: CheckCircle2,
  rejected: XCircle,
  failed: AlertCircle,
  recalled: RotateCcw,
};

const SizeClasses = {
  sm: 'text-[10px] px-1.5 py-0.5 gap-0.5',
  md: 'text-xs px-2 py-1 gap-1',
  lg: 'text-sm px-3 py-1.5 gap-1.5',
};

const IconSizes = {
  sm: 'w-2.5 h-2.5',
  md: 'w-3 h-3',
  lg: 'w-4 h-4',
};

const ColorClasses: Record<string, string> = {
  neutral: 'bg-neutral-500/20 text-neutral-300 border-neutral-500/30',
  sky: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
  amber: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  emerald: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  rose: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showLabel = true,
  showIcon = true,
  className = '',
}) => {
  const config = MESSAGE_STATUS_CONFIG[status];
  const Icon = StatusIcons[status];
  const colorClass = ColorClasses[config.color] || ColorClasses.neutral;

  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-full border
        ${SizeClasses[size]}
        ${colorClass}
        ${className}
      `}
      role="status"
      aria-live="polite"
      aria-label={`Trạng thái: ${config.label}. ${config.description}`}
    >
      {showIcon && (
        <Icon 
          className={`${IconSizes[size]} ${config.animate ? 'animate-spin' : ''}`} 
          aria-hidden="true"
        />
      )}
      {showLabel && <span className="whitespace-nowrap">{config.label}</span>}
    </span>
  );
};

// Status Indicator - simpler version for inline use
export const StatusIndicator: React.FC<{ status: MessageStatus; className?: string }> = ({ 
  status, 
  className = '' 
}) => {
  const config = MESSAGE_STATUS_CONFIG[status];
  const Icon = StatusIcons[status];
  const colorClass = ColorClasses[config.color] || ColorClasses.neutral;

  return (
    <span 
      className={`inline-flex items-center gap-1 ${colorClass} ${className}`}
      role="status"
      aria-label={`Trạng thái: ${config.label}`}
    >
      <Icon className="w-3.5 h-3.5 {config.animate ? 'animate-spin' : ''}" aria-hidden="true" />
      <span className="text-xs font-medium whitespace-nowrap">{config.label}</span>
    </span>
  );
};

// Status Dot - minimal indicator
export const StatusDot: React.FC<{ status: MessageStatus; className?: string }> = ({ 
  status, 
  className = '' 
}) => {
  const config = MESSAGE_STATUS_CONFIG[status];
  
  const dotColors: Record<string, string> = {
    neutral: 'bg-neutral-400',
    sky: 'bg-sky-400',
    amber: 'bg-amber-400',
    emerald: 'bg-emerald-400',
    rose: 'bg-rose-400',
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1
        ${className}
      `}
      role="status"
      aria-label={`Trạng thái: ${config.label}`}
    >
      <span 
        className={`
          w-2 h-2 rounded-full 
          ${dotColors[config.color] || dotColors.neutral}
          ${config.animate ? 'animate-pulse' : ''}
        `}
        aria-hidden="true"
      />
      <span className="text-[11px] font-medium text-neutral-300">{config.label}</span>
    </span>
  );
};