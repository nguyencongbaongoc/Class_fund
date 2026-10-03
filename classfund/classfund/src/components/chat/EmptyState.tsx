import React from 'react';
import { MessageSquare, UploadCloud, Sparkles } from 'lucide-react';
import { LiquidCard } from '../../components/common/LiquidCard';

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  variant?: 'chat' | 'upload' | 'search';
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  variant = 'chat',
}) => {
  const configs = {
    chat: {
      icon: MessageSquare,
      defaultTitle: 'Chưa có tin nhắn nào',
      defaultDescription: 'Hãy là người đầu tiên gửi tin nhắn hoặc ảnh biên lai vào kênh thảo luận lớp.',
      defaultActionLabel: 'Gửi tin nhắn đầu tiên',
    },
    upload: {
      icon: UploadCloud,
      defaultTitle: 'Chưa có ảnh biên lai',
      defaultDescription: 'Tải lên ảnh biên lai chuyển khoản để AI tự động đọc và ghi sổ quỹ.',
      defaultActionLabel: 'Tải ảnh biên lai',
    },
    search: {
      icon: Sparkles,
      defaultTitle: 'Không tìm thấy kết quả',
      defaultDescription: 'Thử tìm kiếm với từ khóa khác hoặc kiểm tra lại bộ lọc.',
      defaultActionLabel: 'Xóa bộ lọc',
    },
  };

  const config = configs[variant];
  const Icon = config.icon;

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <LiquidCard variant="clear" clarity="clear" className="w-full max-w-sm p-8">
        <div className="w-20 h-20 rounded-2xl bg-white/[0.05] border border-white/10 flex items-center justify-center mx-auto mb-6">
          <Icon className="w-10 h-10 text-neutral-400" aria-hidden="true" />
        </div>
        <h3 className="text-lg font-semibold text-white mb-2">
          {title || config.defaultTitle}
        </h3>
        <p className="text-sm text-neutral-400 mb-6 leading-relaxed">
          {description || config.defaultDescription}
        </p>
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full apple-btn-primary font-medium text-sm shadow-md transition-all hover:shadow-lg active:scale-95"
          >
            <Sparkles className="w-4 h-4" aria-hidden="true" />
            {actionLabel}
          </button>
        )}
      </LiquidCard>
    </div>
  );
};

// Loading skeleton for message list
export const LoadingState: React.FC<{ count?: number }> = ({ count = 5 }) => {
  return (
    <div className="space-y-4" role="status" aria-label="Đang tải tin nhắn">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="flex items-start gap-3 animate-pulse">
          {/* Avatar skeleton */}
          <div className="w-8 h-8 rounded-full bg-white/10 shrink-0" />
          <div className="flex-1 space-y-2">
            {/* Sender info skeleton */}
            <div className="flex items-center gap-2">
              <div className="h-3 w-24 bg-white/10 rounded" />
              <div className="h-3 w-16 bg-white/10 rounded" />
              <div className="h-3 w-20 bg-white/10 rounded" />
            </div>
            {/* Message bubble skeleton */}
            <div className="h-12 w-3/4 bg-white/10 rounded-2xl" />
            {/* Second line */}
            <div className="h-8 w-1/2 bg-white/10 rounded-2xl" />
          </div>
        </div>
      ))}
    </div>
  );
};

// Loading state for composer
export const ComposerLoadingState: React.FC = () => {
  return (
    <div className="flex items-center gap-2 p-1.5 rounded-full bg-neutral-900/80 backdrop-blur-2xl border border-white/15">
      <div className="w-9 h-9 rounded-full bg-white/[0.06]" aria-hidden="true" />
      <div className="flex-1 h-8 bg-white/[0.06] rounded-full" />
      <div className="w-24 h-8 bg-white/[0.06] rounded-full" />
    </div>
  );
};