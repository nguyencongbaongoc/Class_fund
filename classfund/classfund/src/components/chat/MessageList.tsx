import React, { useRef, useEffect, useCallback } from 'react';
import { Loader2, MessageSquare } from 'lucide-react';
import { LiquidCard } from '../../components/common/LiquidCard';
import { Message, MessageStatus } from '../../types/chat';
import { MessageItem } from './MessageItem';
import { EmptyState, LoadingState } from './EmptyState';
import { StatusBadge } from './StatusBadge';

interface MessageListProps {
  messages: Message[];
  currentUserId: string | null;
  isLoading: boolean;
  onRecall: (messageId: string, status: MessageStatus, reason?: string) => void;
  canRecall: (message: Message) => boolean;
  isRecalling?: (messageId: string) => boolean;
  onViewReceipt?: (entryId: string) => void;
  pinnedMessage?: Message;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  currentUserId,
  isLoading,
  onRecall,
  canRecall,
  isRecalling,
  onViewReceipt,
  pinnedMessage,
}) => {
  const endRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (messages.length > 0 && !isLoading) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, isLoading]);

  // Scroll to bottom helper
  const scrollToBottom = useCallback(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  if (isLoading) {
    return (
      <LiquidCard variant="default" clarity="balanced" className="p-4 min-h-[480px] max-h-[620px]">
        <LoadingState count={6} />
      </LiquidCard>
    );
  }

  if (messages.length === 0) {
    return (
      <LiquidCard variant="default" clarity="balanced" className="p-4 min-h-[480px] max-h-[620px] flex items-center justify-center">
        <EmptyState 
          variant="chat"
          actionLabel={currentUserId ? 'Gửi tin nhắn đầu tiên' : undefined}
          onAction={scrollToBottom}
        />
      </LiquidCard>
    );
  }

  return (
    <LiquidCard variant="default" clarity="balanced" className="p-4 min-h-[480px] max-h-[620px] overflow-y-auto flex flex-col-reverse">
      {/* Pinned message */}
      {pinnedMessage && (
        <div className="mb-4" data-pinned="true">
          <MessageItem
            message={pinnedMessage}
            isOwn={pinnedMessage.sender_id === currentUserId}
            onRecall={onRecall}
            canRecall={false}
            onViewReceipt={onViewReceipt}
          />
        </div>
      )}

      {/* Message list */}
      <div role="log" aria-live="polite" aria-label="Danh sách tin nhắn">
        {messages.map((message) => (
          <div key={message.id} data-message-id={message.id}>
            <MessageItem
              message={message}
              isOwn={message.sender_id === currentUserId}
              onRecall={onRecall}
              canRecall={canRecall(message)}
              isRecalling={isRecalling ? isRecalling(message.id) : false}
              onViewReceipt={onViewReceipt}
            />
          </div>
        ))}
      </div>

      <div ref={endRef} style={{ height: 1 }} />
    </LiquidCard>
  );
};

// Alternative non-virtualized version for simpler cases (same as above now)
export const SimpleMessageList: React.FC<MessageListProps> = ({
  messages,
  currentUserId,
  isLoading,
  onRecall,
  canRecall,
  isRecalling,
  onViewReceipt,
  pinnedMessage,
}) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messages.length > 0 && !isLoading) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, isLoading]);

  if (isLoading) {
    return (
      <LiquidCard variant="default" clarity="balanced" className="p-4 min-h-[480px] max-h-[620px]">
        <LoadingState count={6} />
      </LiquidCard>
    );
  }

  if (messages.length === 0) {
    return (
      <LiquidCard variant="default" clarity="balanced" className="p-4 min-h-[480px] max-h-[620px] flex items-center justify-center">
        <EmptyState variant="chat" />
      </LiquidCard>
    );
  }

  return (
    <LiquidCard variant="default" clarity="balanced" className="p-4 min-h-[480px] max-h-[620px] overflow-y-auto flex flex-col-reverse">
      {pinnedMessage && (
        <div className="mb-4">
          <MessageItem
            message={pinnedMessage}
            isOwn={pinnedMessage.sender_id === currentUserId}
            onRecall={onRecall}
            canRecall={false}
            onViewReceipt={onViewReceipt}
          />
        </div>
      )}

      <div role="log" aria-live="polite" aria-label="Danh sách tin nhắn">
        {messages.map((message) => (
          <div key={message.id} data-message-id={message.id}>
            <MessageItem
              message={message}
              isOwn={message.sender_id === currentUserId}
              onRecall={onRecall}
              canRecall={canRecall(message)}
              isRecalling={isRecalling ? isRecalling(message.id) : false}
              onViewReceipt={onViewReceipt}
            />
          </div>
        ))}
      </div>

      <div ref={endRef} style={{ height: 1 }} />
    </LiquidCard>
  );
};