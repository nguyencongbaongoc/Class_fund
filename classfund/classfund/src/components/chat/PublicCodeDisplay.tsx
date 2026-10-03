import React, { useState } from 'react';
import { Copy, Check, Hash } from 'lucide-react';

interface PublicCodeDisplayProps {
  code?: string;
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const PublicCodeDisplay: React.FC<PublicCodeDisplayProps> = ({
  code,
  label = 'Mã tham chiếu',
  size = 'md',
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  if (!code) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const SizeClasses = {
    sm: 'text-[10px] gap-1 px-2 py-1',
    md: 'text-xs gap-1.5 px-2.5 py-1.5',
  };

  const IconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
  };

  return (
    <div 
      className={`
        inline-flex items-center rounded-xl border border-white/10 bg-white/[0.03] 
        ${SizeClasses[size]} ${className}
      `}
      role="group"
      aria-label={label}
    >
      <Hash className={`${IconSizes[size]} text-neutral-400 shrink-0`} aria-hidden="true" />
      <span className="font-mono text-neutral-200 select-all">{code}</span>
      <button
        onClick={handleCopy}
        className={`
          ml-1 p-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] transition-colors
          ${copied ? 'text-emerald-400' : 'text-neutral-500 hover:text-white'}
        `}
        aria-label={copied ? 'Đã sao chép' : 'Sao chép mã tham chiếu'}
        title={copied ? 'Đã sao chép!' : 'Sao chép mã'}
      >
        {copied ? (
          <Check className={`${IconSizes[size]} fill-current`} aria-hidden="true" />
        ) : (
          <Copy className={`${IconSizes[size]}`} aria-hidden="true" />
        )}
      </button>
    </div>
  );
};

// Inline version for compact display
export const InlinePublicCode: React.FC<{ code?: string }> = ({ code }) => {
  if (!code) return null;
  
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-mono text-neutral-400">
      <Hash className="w-2.5 h-2.5" aria-hidden="true" />
      <span>{code}</span>
    </span>
  );
};